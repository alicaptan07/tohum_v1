import "@/styles/globals.css";

export default function App({ Component, pageProps }) {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Component {...pageProps} />
    </main>
  );
}
