import "./globals.css";

export const metadata = {
  title: "Remote Job Guardian",
  description: "AI-assisted verifier for high-quality remote jobs"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}