import { BrowserRouter, Routes, Route } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";

import LandingPage from "@/pages/LandingPage";
import DashboardPage from "@/pages/DashboardPage";
import UploadReportPage from "@/pages/UploadReportPage";
import AnalysisPage from "@/pages/AnalysisPage";

import RootLayout from "@/components/layout/RootLayout";
import DashboardLayout from "@/components/layout/DashboardLayout";

function App() {
  return (
    <TooltipProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<RootLayout />}>
            <Route path="/" element={<LandingPage />} />
          </Route>
          
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadReportPage />} />
            <Route path="/analysis/:id" element={<AnalysisPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  );
}

export default App;
