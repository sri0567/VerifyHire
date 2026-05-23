import "./globals.css";

export const metadata = {
  title: "VerifyHire",
  description: "AI-assisted verifier and tracker for high-quality remote jobs"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}