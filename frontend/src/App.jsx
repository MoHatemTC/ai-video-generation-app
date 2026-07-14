import { Routes, Route, Link } from "react-router-dom";
import RequestPage from "./pages/RequestPage.jsx";
import StatusPage from "./pages/StatusPage.jsx";

export default function App() {
  return (
    <div className="container">
      <h1>
        <Link to="/" style={{ color: "inherit", textDecoration: "none" }}>
          🎬 Sprints Video Studio
        </Link>
      </h1>
      <Routes>
        <Route path="/" element={<RequestPage />} />
        <Route path="/videos/:id" element={<StatusPage />} />
      </Routes>
    </div>
  );
}
