export default function Loading() {
  return (
    <main className="mx-auto w-full max-w-[1680px] px-4 pt-4 lg:px-6" aria-busy="true" aria-label="Loading match">
      <div className="mb-4 h-16 w-80 animate-pulse rounded-md bg-s2" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,400px)]">
        <div className="aspect-video animate-pulse rounded-[10px] bg-s2" />
        <div className="hidden animate-pulse rounded-[10px] bg-s2 lg:block" />
      </div>
      <div className="mt-4 h-72 animate-pulse rounded-[10px] bg-s2" />
    </main>
  );
}
