interface PlaceholderPageProps {
  title: string;
  description: string;
}

export default function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-white p-6">
      <section className="w-full max-w-lg rounded-2xl border border-neutral-200 p-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500">
          Habit Tracker
        </p>
        <h1 className="mt-4 text-3xl font-bold text-neutral-900">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-neutral-600">{description}</p>
      </section>
    </main>
  );
}
