package dev.httpcapture.capture_app

import android.content.Context
import android.util.AtomicFile
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.io.File
import java.math.BigInteger
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.SecureRandom
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.security.cert.CertPathValidator
import java.security.cert.PKIXParameters
import java.security.cert.TrustAnchor
import org.bouncycastle.asn1.x509.SubjectKeyIdentifier
import org.bouncycastle.asn1.x509.AuthorityKeyIdentifier
import org.bouncycastle.cert.jcajce.JcaX509CertificateHolder
import org.bouncycastle.cert.jcajce.JcaX509ExtensionUtils
import java.util.Date
import javax.security.auth.x500.X500Principal
import org.bouncycastle.asn1.x500.X500Name
import org.bouncycastle.asn1.x509.BasicConstraints
import org.bouncycastle.asn1.x509.Extension
import org.bouncycastle.asn1.x509.ExtendedKeyUsage
import org.bouncycastle.asn1.x509.GeneralName
import org.bouncycastle.asn1.x509.GeneralNames
import org.bouncycastle.asn1.x509.KeyPurposeId
import org.bouncycastle.asn1.x509.KeyUsage
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder

/** Root key is non-exportable AndroidKeyStore material. Only leaf keys cross app-local IPC. */
class CertificateAuthority(private val context: Context) {
    private val alias = "http-capture-root-v1"
    private val rootFile get() = File(context.noBackupFilesDir, "http-capture-root.crt")
    private val rootStorage get() = AtomicFile(rootFile)
    private val keys get() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    private fun serial() = BigInteger(159, SecureRandom()).add(BigInteger.ONE)
    private fun pem(type: String, bytes: ByteArray) = "-----BEGIN $type-----\n" + Base64.encodeToString(bytes, Base64.NO_WRAP).chunked(64).joinToString("\n") + "\n-----END $type-----\n"
    @Synchronized private fun root(): X509Certificate {
        if ((rootFile.exists() || File(rootFile.path + ".bak").exists()) && keys.containsAlias(alias)) return CertificateFactory.getInstance("X.509").generateCertificate(rootStorage.openRead().use { it.readBytes().inputStream() }) as X509Certificate
        if (!keys.containsAlias(alias)) {
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore").apply {
                initialize(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
                    .setKeySize(2048).setDigests(KeyProperties.DIGEST_SHA256).setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                    .setCertificateSubject(X500Principal("CN=HTTP Capture Local Root")).build())
            }.generateKeyPair()
        }
        return issueRoot()
    }
    private fun fingerprint(cert: X509Certificate) =
        MessageDigest.getInstance("SHA-256").digest(cert.encoded).joinToString(":") { "%02X".format(it) }
    private fun issueRoot(): X509Certificate {
        val key = keys.getKey(alias, null) as PrivateKey
        val publicKey = keys.getCertificate(alias).publicKey
        val subject = X500Name("CN=HTTP Capture Local Root")
        val builder = JcaX509v3CertificateBuilder(subject, serial(),
            Date(System.currentTimeMillis()-86400000L),
            Date(System.currentTimeMillis()+5*365*86400000L), subject, publicKey)
        builder.addExtension(Extension.basicConstraints, true, BasicConstraints(0))
        builder.addExtension(Extension.keyUsage, true, KeyUsage(KeyUsage.keyCertSign or KeyUsage.cRLSign))
        val identifiers = JcaX509ExtensionUtils()
        builder.addExtension(Extension.subjectKeyIdentifier, false, identifiers.createSubjectKeyIdentifier(publicKey))
        builder.addExtension(Extension.authorityKeyIdentifier, false, identifiers.createAuthorityKeyIdentifier(publicKey))
        val encoded = builder.build(JcaContentSignerBuilder("SHA256withRSA").build(key)).encoded
        val cert = CertificateFactory.getInstance("X.509").generateCertificate(encoded.inputStream()) as X509Certificate
        cert.verify(publicKey)
        cert.checkValidity()
        check(hasIdentifiers(cert)) { "Root certificate identifiers missing" }
        val output = rootStorage.startWrite()
        try {
            output.write(encoded)
            rootStorage.finishWrite(output)
        } catch (error: Exception) {
            rootStorage.failWrite(output)
            throw error
        }
        return cert
    }
    private fun hasIdentifiers(cert: X509Certificate) =
        cert.getExtensionValue(Extension.subjectKeyIdentifier.id) != null &&
        cert.getExtensionValue(Extension.authorityKeyIdentifier.id) != null

    /** Existing certificates stay unchanged until explicit consent. The key is retained. */
    @Synchronized fun upgrade(consent: Boolean): Map<String, Any> {
        require(consent) { "Explicit certificate replacement consent required" }
        val previous = root()
        if (!hasIdentifiers(previous)) {
            File(context.noBackupFilesDir, "previous-root-${fingerprint(previous).replace(":", "").takeLast(8)}.crt")
                .writeBytes(previous.encoded)
            issueRoot()
        }
        return info()
    }
    @Synchronized fun info(): Map<String, Any> {
        val cert = root()
        val trust = KeyStore.getInstance("AndroidCAStore").apply { load(null) }
        val trusted = trust.aliases().toList().any { trust.getCertificate(it)?.encoded?.contentEquals(cert.encoded) == true }
        // Public certificate only, made available to the user-selected document provider.
        val export = File(context.filesDir, "HTTP-Capture-Root.crt").apply { writeBytes(cert.encoded) }
        return mapOf("path" to export.path, "pem" to pem("CERTIFICATE",cert.encoded), "trusted" to trusted,
            "fingerprint" to fingerprint(cert), "profileCurrent" to hasIdentifiers(cert))
    }
    @Synchronized fun leaf(host: String): Map<String, String> {
        require(host.length in 1..253 && host.matches(Regex("[a-zA-Z0-9.:-]+"))) { "Invalid TLS host" }
        val ca = root(); ca.checkValidity()
        val pair = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
        val name = X500Name("CN=$host")
        val builder = JcaX509v3CertificateBuilder(X500Name(ca.subjectX500Principal.name), serial(), Date(maxOf(System.currentTimeMillis()-3600000L, ca.notBefore.time)), Date(minOf(System.currentTimeMillis()+7*86400000L, ca.notAfter.time)), name, pair.public)
        builder.addExtension(Extension.basicConstraints, true, BasicConstraints(false))
        builder.addExtension(Extension.keyUsage, true, KeyUsage(KeyUsage.digitalSignature or KeyUsage.keyEncipherment))
        builder.addExtension(Extension.extendedKeyUsage, false, ExtendedKeyUsage(KeyPurposeId.id_kp_serverAuth))
        val identifiers = JcaX509ExtensionUtils()
        builder.addExtension(Extension.subjectKeyIdentifier, false, identifiers.createSubjectKeyIdentifier(pair.public))
        builder.addExtension(Extension.authorityKeyIdentifier, false, identifiers.createAuthorityKeyIdentifier(ca))
        val ip = host.contains(':') || host.matches(Regex("[0-9.]+"))
        builder.addExtension(Extension.subjectAlternativeName, false, GeneralNames(GeneralName(if(ip) GeneralName.iPAddress else GeneralName.dNSName, host)))
        val cert = builder.build(JcaContentSignerBuilder("SHA256withRSA").build(keys.getKey(alias,null) as PrivateKey)).encoded
        val leaf = CertificateFactory.getInstance("X.509").generateCertificate(cert.inputStream()) as X509Certificate
        validateLeaf(ca, leaf, host)
        return mapOf("certificate" to pem("CERTIFICATE",cert)+pem("CERTIFICATE",ca.encoded), "key" to pem("PRIVATE KEY",pair.private.encoded))
    }

    private fun validateLeaf(ca: X509Certificate, leaf: X509Certificate, host: String) {
        leaf.checkValidity()
        leaf.verify(ca.publicKey)
        check(leaf.basicConstraints == -1 && leaf.keyUsage[0]) { "Invalid server certificate constraints" }
        check(leaf.extendedKeyUsage.contains(KeyPurposeId.id_kp_serverAuth.id)) { "Server authentication EKU missing" }
        val sanType = if (host.contains(':') || host.matches(Regex("[0-9.]+"))) 7 else 2
        check(leaf.subjectAlternativeNames.any { san ->
            (san[0] as Int) == sanType &&
            (if (sanType == 7) java.net.InetAddress.getByName(san[1] as String) == java.net.InetAddress.getByName(host)
             else (san[1] as String).equals(host, ignoreCase = true))
        }) { "Server certificate SAN does not match host" }
        val holder = JcaX509CertificateHolder(leaf)
        val ski = SubjectKeyIdentifier.getInstance(holder.getExtension(Extension.subjectKeyIdentifier).parsedValue)
        val aki = AuthorityKeyIdentifier.getInstance(holder.getExtension(Extension.authorityKeyIdentifier).parsedValue)
        val identifiers = JcaX509ExtensionUtils()
        check(ski.keyIdentifier.contentEquals(identifiers.createSubjectKeyIdentifier(leaf.publicKey).keyIdentifier))
        check(aki.keyIdentifier.contentEquals(identifiers.createAuthorityKeyIdentifier(ca).keyIdentifier))
        val path = CertificateFactory.getInstance("X.509").generateCertPath(listOf(leaf))
        val parameters = PKIXParameters(setOf(TrustAnchor(ca, null))).apply { isRevocationEnabled = false }
        // Explicit local test anchor validates issuance; it does not change any app/OS trust.
        CertPathValidator.getInstance("PKIX").validate(path, parameters)
    }

    /** Exercise the same issuer used by real CONNECT requests; export public evidence only. */
    @Synchronized fun checkProfile(): Map<String, Any> {
        val ca = root()
        check(hasIdentifiers(ca)) { "Legacy CA profile. Use certificate profile upgrade and install the new public CA." }
        ca.checkValidity()
        ca.verify(ca.publicKey)
        check(runCatching { upgrade(false) }.isFailure) { "CA upgrade accepted without consent" }
        check(root().encoded.contentEquals(ca.encoded)) { "CA changed without consent" }
        val rootHolder = JcaX509CertificateHolder(ca)
        val rootSki = SubjectKeyIdentifier.getInstance(rootHolder.getExtension(Extension.subjectKeyIdentifier).parsedValue)
        val rootAki = AuthorityKeyIdentifier.getInstance(rootHolder.getExtension(Extension.authorityKeyIdentifier).parsedValue)
        check(rootSki.keyIdentifier.contentEquals(rootAki.keyIdentifier))
        check(rootSki.keyIdentifier.contentEquals(JcaX509ExtensionUtils().createSubjectKeyIdentifier(ca.publicKey).keyIdentifier))
        val hosts = listOf("login.microsoftonline.com", "api.onedrive.com", "recent.svc.cloud.microsoft", "d.docs.live.net", "127.0.0.1", "::1")
        val debug = (context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0
        val folder = File(context.filesDir, "certificate-profile-check")
        if (debug) {
            folder.mkdirs()
            File(folder, "root.pem").writeText(pem("CERTIFICATE", ca.encoded))
        }
        hosts.forEachIndexed { index, host ->
            val identity = leaf(host)
            if (debug) {
                // The returned key is deliberately excluded from this evidence.
                val chain = identity.getValue("certificate")
                File(folder, "leaf-$index.pem").writeText(chain.substringBefore("-----END CERTIFICATE-----") + "-----END CERTIFICATE-----\n")
            }
        }
        val report = mapOf<String, Any>("status" to "passed", "rootSkiAkiMatch" to true,
            "leafSkiAkiSanEkuSignaturePkix" to true, "consentRequiredAndCaPreserved" to true, "hosts" to hosts, "fingerprint" to fingerprint(ca),
            "officeAppTrust" to "not tested", "privateKeysExported" to false)
        if (debug) File(folder, "report.json").writeText(org.json.JSONObject(report).toString())
        return report
    }
}
