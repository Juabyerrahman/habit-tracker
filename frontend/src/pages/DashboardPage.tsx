
function DashboardPage() {
  const today = new Date();

  const formattedDate = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(today);

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 md:flex">

      {/* Sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-neutral-200 bg-white p-6 md:flex md:flex-col">
        <div className="mb-12">
          <h1 className="text-xl font-bold tracking-tight">
            Habit Tracker<span className="text-neutral-400">.</span>
          </h1>
          <p className="mt-1 text-xs text-neutral-400">
            Build better days.
          </p>
        </div>

        <nav className="space-y-2">
          <a href="/" className="flex items-center rounded-lg bg-neutral-900 px-4 py-3 text-sm font-medium text-white">
            <span className="mr-3">▦</span>
            Dashboard
          </a>

          <a href="#habits" className="flex items-center rounded-lg px-4 py-3 text-sm text-neutral-600 hover:bg-neutral-100">
            <span className="mr-3">◷</span>
            My Habits
          </a>

          <a href="#tasks" className="flex items-center rounded-lg px-4 py-3 text-sm text-neutral-600 hover:bg-neutral-100">
            <span className="mr-3">☑</span>
            Daily Tasks
          </a>

          <a href="#reports" className="flex items-center rounded-lg px-4 py-3 text-sm text-neutral-600 hover:bg-neutral-100">
            <span className="mr-3">▤</span>
            Reports
          </a>
        </nav>

        <div className="mt-auto border-t border-neutral-200 pt-5">
          <p className="text-xs text-neutral-400">PERSONAL WORKSPACE</p>
          <p className="mt-2 text-sm font-medium">Your progress matters.</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="min-w-0 flex-1 p-5 md:p-10">

        {/* Header */}
        <header className="mb-9 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-neutral-500">{formattedDate}</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight">
              Dashboard
            </h2>
            <p className="mt-2 text-sm text-neutral-500">
              Stay consistent. Make every day count.
            </p>
          </div>

          <button className="rounded-lg bg-neutral-900 px-5 py-3 text-sm font-medium text-white hover:bg-neutral-700">
            + Add Habit
          </button>
        </header>

        {/* Summary cards */}
        <section className="mb-9 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[
            { title: "Habits tracked", value: "—" },
            { title: "Today's progress", value: "—" },
            { title: "Current best streak", value: "—" },
            { title: "Monthly completion", value: "—" },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-xl border border-neutral-200 bg-white p-5"
            >
              <p className="text-xs font-medium text-neutral-500">
                {item.title}
              </p>
              <p className="mt-4 text-3xl font-semibold tracking-tight">
                {item.value}
              </p>
            </div>
          ))}
        </section>

        {/* Monthly habits */}
        <section
          id="habits"
          className="mb-8 rounded-xl border border-neutral-200 bg-white p-6"
        >
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold">Monthly habit tracker</h3>
              <p className="mt-1 text-sm text-neutral-500">
                Track your consistency day by day.
              </p>
            </div>

            <button className="rounded-lg border border-neutral-200 px-4 py-2 text-sm hover:bg-neutral-50">
              View all habits
            </button>
          </div>

          <div className="flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed border-neutral-200 text-center">
            <p className="text-sm font-medium text-neutral-700">
              Your monthly habit grid will appear here.
            </p>
            <p className="mt-2 max-w-sm text-xs leading-5 text-neutral-400">
              Once your habits are created, you'll be able to track daily
              completion, streaks and monthly progress here.
            </p>
          </div>
        </section>

        {/* Daily tasks */}
        <section
          id="tasks"
          className="mb-8 rounded-xl border border-neutral-200 bg-white p-6"
        >
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Today's tasks</h3>
              <p className="mt-1 text-sm text-neutral-500">
                Your flexible daily to-do list.
              </p>
            </div>

            <button className="rounded-lg border border-neutral-200 px-4 py-2 text-sm hover:bg-neutral-50">
              + Add task
            </button>
          </div>

          <div className="flex min-h-28 items-center justify-center rounded-lg border border-dashed border-neutral-200">
            <p className="text-sm text-neutral-400">
              No tasks displayed yet.
            </p>
          </div>
        </section>

        {/* Reports */}
        <section
          id="reports"
          className="rounded-xl border border-neutral-200 bg-white p-6"
        >
          <h3 className="text-lg font-semibold">Progress reports</h3>
          <p className="mt-2 text-sm text-neutral-500">
            Weekly and monthly insights will appear here.
          </p>
        </section>

      </main>
    </div>
  );
}

export default DashboardPage;
