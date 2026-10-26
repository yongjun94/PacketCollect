package dev.httpcapture.capture_app

import android.content.Context
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
    private val keys get() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    private fun serial() = BigInteger(159, SecureRandom()).add(BigInteger.ONE)
    private fun pem(type: String, bytes: ByteArray) = "-----BEGIN $type-----\n" + Base64.encodeToString(bytes, Base64.NO_WRAP).chunked(64).joinToString("\n") + "\n-----END $type-----\n"
    @Synchronized private fun root(): X509Certificate {
        if (rootFile.exists() && keys.containsAlias(alias)) return CertificateFactory.getInstance("X.509").generateCertificate(rootFile.inputStream().use { it.readBytes().inputStream() }) as X509Certificate
        if (!keys.containsAlias(alias)) {
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore").apply {
                initialize(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
                    .setKeySize(2048).setDigests(KeyProperties.DIGEST_SHA256).setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                    .setCertificateSubject(X500Principal("CN=HTTP Capture Local Root")).build())
            }.generateKeyPair()
        }
        val key = keys.getKey(alias, null) as PrivateKey
        val subject = X500Name("CN=HTTP Capture Local Root")
        val builder = JcaX509v3CertificateBuilder(subject, serial(), Date(System.currentTimeMillis()-86400000L), Date(System.currentTimeMillis()+5*365*86400000L), subject, keys.getCertificate(alias).publicKey)
        builder.addExtension(Extension.basicConstraints, true, BasicConstraints(0))
        builder.addExtension(Extension.keyUsage, true, KeyUsage(KeyUsage.keyCertSign or KeyUsage.cRLSign))
        val encoded = builder.build(JcaContentSignerBuilder("SHA256withRSA").build(key)).encoded
        val temp = File(context.noBackupFilesDir, "root.tmp")
        temp.writeBytes(encoded)
        check(temp.renameTo(rootFile)) { "Cannot persist CA certificate" }
        return CertificateFactory.getInstance("X.509").generateCertificate(encoded.inputStream()) as X509Certificate
    }
    @Synchronized fun info(): Map<String, Any> {
        val cert = root()
        val trust = KeyStore.getInstance("AndroidCAStore").apply { load(null) }
        val trusted = trust.aliases().toList().any { trust.getCertificate(it)?.encoded?.contentEquals(cert.encoded) == true }
        // Public certificate only, made available to the user-selected document provider.
        val export = File(context.filesDir, "HTTP-Capture-Root.crt").apply { writeBytes(cert.encoded) }
        return mapOf("path" to export.path, "pem" to pem("CERTIFICATE",cert.encoded), "trusted" to trusted,
            "fingerprint" to MessageDigest.getInstance("SHA-256").digest(cert.encoded).joinToString(":") { "%02X".format(it) })
    }
    @Synchronized fun leaf(host: String): Map<String, String> {
        require(host.length in 1..253 && host.matches(Regex("[a-zA-Z0-9.:-]+"))) { "Invalid TLS host" }
        val ca = root(); ca.checkValidity()
        val pair = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
        val name = X500Name("CN=$host")
        val builder = JcaX509v3CertificateBuilder(X500Name(ca.subjectX500Principal.name), serial(), Date(System.currentTimeMillis()-3600000L), Date(System.currentTimeMillis()+7*86400000L), name, pair.public)
        builder.addExtension(Extension.basicConstraints, true, BasicConstraints(false))
        builder.addExtension(Extension.keyUsage, true, KeyUsage(KeyUsage.digitalSignature or KeyUsage.keyEncipherment))
        builder.addExtension(Extension.extendedKeyUsage, false, ExtendedKeyUsage(KeyPurposeId.id_kp_serverAuth))
        val ip = host.contains(':') || host.matches(Regex("[0-9.]+"))
        builder.addExtension(Extension.subjectAlternativeName, false, GeneralNames(GeneralName(if(ip) GeneralName.iPAddress else GeneralName.dNSName, host)))
        val cert = builder.build(JcaContentSignerBuilder("SHA256withRSA").build(keys.getKey(alias,null) as PrivateKey)).encoded
        return mapOf("certificate" to pem("CERTIFICATE",cert)+pem("CERTIFICATE",ca.encoded), "key" to pem("PRIVATE KEY",pair.private.encoded))
    }
}
