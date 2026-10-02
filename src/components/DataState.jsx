export default function DataState({ query }) {
  if (query.isError) return <div role="alert" className="p-5 rounded-xl bg-amber-50 text-amber-900 my-4">
    <p>{query.error.message}</p>
    <button className="underline mt-2" onClick={() => query.refetch()}>Retry</button>
  </div>;
  if (query.isPending) return <p role="status" className="py-10 text-slate-500">Loading research data…</p>;
  return null;
}
