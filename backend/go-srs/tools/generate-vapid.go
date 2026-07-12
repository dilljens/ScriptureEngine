// Generate VAPID keys for Web Push Protocol.
//
// Usage:
//   go run tools/generate-vapid.go
//
// Output:
//   VAPID_PUBLIC_KEY=<key>
//   VAPID_PRIVATE_KEY=<key>
//
// Set these as environment variables when running the server.

package main

import (
	"crypto/rand"
	"crypto/ecdsa"
	"crypto/elliptic"
	"encoding/base64"
	"fmt"
)

func main() {
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		panic(err)
	}

	// Public key in uncompressed point format
	pub := append(key.PublicKey.X.Bytes(), key.PublicKey.Y.Bytes()...)
	pubKey := base64.RawURLEncoding.EncodeToString(pub)

	// Private key in big-endian format
	priv := key.D.Bytes()
	// Pad to 32 bytes
	for len(priv) < 32 {
		priv = append([]byte{0}, priv...)
	}
	privKey := base64.RawURLEncoding.EncodeToString(priv)

	fmt.Println("VAPID_PUBLIC_KEY=" + pubKey)
	fmt.Println("VAPID_PRIVATE_KEY=" + privKey)
	fmt.Println()
	fmt.Println("Set these in your environment and restart the server.")
}
