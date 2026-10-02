import { Link } from 'react-router-dom';
export default function PageNotFound() {
  return <div className="max-w-xl mx-auto px-5 py-20 text-center">
    <h1 className="text-3xl font-semibold">Page not found</h1>
    <p className="text-slate-600 my-5">This page is not part of the Lagos research pilot.</p>
    <Link to="/" className="text-teal-700 underline">Return to the pilot</Link>
  </div>;
}
