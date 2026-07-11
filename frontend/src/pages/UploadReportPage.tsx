import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate, useLocation } from "react-router-dom";
import { UploadCloud, FileText, CheckCircle2, Loader2, FileUp, Zap, ShieldCheck, BarChart3, BrainCircuit, Search, TrendingUp, LayoutDashboard } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { reportService } from "@/lib/api";

const processingSteps = [
  { id: "upload", text: "Uploading PDF...", icon: FileUp, color: "text-blue-500" },
  { id: "ocr", text: "Running OCR...", icon: Search, color: "text-cyan-500" },
  { id: "nlp", text: "Running NLP...", icon: BrainCircuit, color: "text-purple-500" },
  { id: "extract", text: "Extracting Financial Data...", icon: FileText, color: "text-indigo-500" },
  { id: "ratios", text: "Calculating Financial Ratios...", icon: BarChart3, color: "text-emerald-500" },
  { id: "fraud", text: "Running Fraud Detection...", icon: ShieldCheck, color: "text-rose-500" },
  { id: "risk", text: "Running Risk Prediction...", icon: Zap, color: "text-amber-500" },
  { id: "forecast", text: "Generating Forecast...", icon: TrendingUp, color: "text-blue-400" },
  { id: "prep", text: "Preparing Dashboard...", icon: LayoutDashboard, color: "text-primary" },
];

export default function UploadReportPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "processing" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [generatedId, setGeneratedId] = useState<string | null>(null);
  const generatedIdRef = useRef<string | null>(null);
  const [preloadedML, setPreloadedML] = useState<any>(null);
  const preloadedMLRef = useRef<any>(null);
  const navigate = useNavigate();

  const isProcessingRef = useRef(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (selectedFile: File) => {
    if (selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      startProcessing(selectedFile);
    } else {
      alert("Please upload a valid PDF file.");
    }
  };

  const startProcessing = async (selectedFile: File) => {
    setStatus("processing");
    setCurrentStepIndex(0);
    setProgress(0);
    isProcessingRef.current = true;

    try {
      // Step 1: Upload
      const uploadRes = await reportService.uploadReport(selectedFile);
      const reportId = uploadRes.data.id;
      
      setCurrentStepIndex(2); // Fast forward some UI steps
      setProgress(20);
      
      // Step 2: Trigger Analysis Pipeline
      const res = await reportService.getReportAnalysis(reportId);
      const ratiosRes = await reportService.calculateRatios(reportId);

      // Extract Data for ML
      const finData = res.data.financial_data || {};
      const ratios = ratiosRes.data.ratios || {};
      const riskPayload = {
        Year: 2024,
        Industry_Type: "Technology",
        Firm_Size: "Large",
        Total_Assets: finData.total_assets || 100000,
        Total_Liabilities: finData.total_liabilities || 50000,
        Total_Revenue: finData.revenue || 150000,
        Net_Income: finData.net_income || 20000,
        Current_Assets: finData.total_assets ? finData.total_assets * 0.6 : 60000,
        Current_Liabilities: finData.total_liabilities ? finData.total_liabilities * 0.5 : 25000,
        Cash_Flow: finData.net_income ? finData.net_income * 1.2 : 24000,
        Debt_to_Equity_Ratio: ratios.debt_to_equity || 0.5,
        Current_Ratio: ratios.current_ratio || 2.0,
        Quick_Ratio: ratios.quick_ratio || 1.5,
        Return_on_Assets: ratios.roa || 0.1,
        Return_on_Equity: ratios.roe || 0.15,
        Gross_Profit_Margin: ratios.gross_margin || 0.4,
        Operating_Margin: ratios.operating_margin || 0.2,
        Asset_Turnover_Ratio: ratios.asset_turnover || 0.8,
        Interest_Coverage_Ratio: ratios.interest_coverage || 5.0,
        Working_Capital: (finData.total_assets && finData.total_liabilities) ? finData.total_assets * 0.6 - finData.total_liabilities * 0.5 : 35000,
        Revenue_Growth_Rate: 0.1,
        Net_Profit_Growth_Rate: 0.12,
        Cash_Flow_Ratio: 1.1
      };

      const ocrText = res.data.extracted_text;
      const textPayload = typeof ocrText === 'string' && ocrText.length > 0 ? ocrText : "Normal financial operations with stable growth.";

      // fetch real stock history from the backend csv files
      // (falls back to a tiny dummy if the fetch fails — better than crashing)
      let forecastPayload: any[] = [];
      try {
        const stockRes = await reportService.getStockData("combined");
        forecastPayload = stockRes.data.history;
      } catch (e) {
        console.warn("Could not load stock data, using fallback", e);
        forecastPayload = [
          { Date: "2024-01-01", Close: 150.0 },
          { Date: "2024-02-01", Close: 155.0 },
          { Date: "2024-03-01", Close: 160.0 },
          { Date: "2024-04-01", Close: 158.0 },
          { Date: "2024-05-01", Close: 165.0 },
        ];
      }

      // Run ML models in parallel to minimize wait time
      const [riskRes, fraudRes, forecastRes] = await Promise.allSettled([
        reportService.predictRisk(riskPayload),
        reportService.predictFraud(textPayload),
        reportService.predictForecast(forecastPayload, 30)
      ]);

      const newMLData = {
        riskData: riskRes.status === 'fulfilled' ? riskRes.value.data : null,
        fraudData: fraudRes.status === 'fulfilled' ? fraudRes.value.data : null,
        forecastData: forecastRes.status === 'fulfilled' ? forecastRes.value.data : null,
      };
      
      setPreloadedML(newMLData);
      preloadedMLRef.current = newMLData;

      setGeneratedId(reportId);
      generatedIdRef.current = reportId;
      isProcessingRef.current = false;
      
    } catch (err: any) {
      isProcessingRef.current = false;
      setStatus("error");
      setErrorMsg(err.response?.data?.detail || "An error occurred during analysis.");
    }
  };

  useEffect(() => {
    if (status === "processing") {
      const stepDuration = 2000; // Fake slow UI interval
      const totalSteps = processingSteps.length;
      
      const interval = setInterval(() => {
        setCurrentStepIndex((prev) => {
          // If backend finished, zip to the end
          if (!isProcessingRef.current) {
            clearInterval(interval);
            setStatus("success");
            setTimeout(() => {
              navigate(`/analysis/${generatedIdRef.current || 'latest'}`, {
                state: { preloadedML: preloadedMLRef.current }
              });
            }, 1500);
            return totalSteps - 1;
          }
          
          if (prev < totalSteps - 2) {
            return prev + 1;
          }
          return prev;
        });
      }, stepDuration);

      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (!isProcessingRef.current) {
             clearInterval(progressInterval);
             return 100;
          }
          if (prev >= 90) return 90; // Hold at 90% until backend finishes
          return prev + 2;
        });
      }, 200);

      return () => {
        clearInterval(interval);
        clearInterval(progressInterval);
      };
    }
  }, [status, navigate, generatedId]);

  return (
    <div className="max-w-4xl mx-auto py-12 animate-in fade-in duration-500">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Upload Financial Report</h1>
        <p className="text-muted-foreground">Upload an annual report or financial statement in PDF format for instant AI analysis.</p>
      </div>

      <AnimatePresence mode="wait">
        {status === "idle" && (
          <motion.div
            key="upload"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <label
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`
                relative flex flex-col items-center justify-center w-full h-[400px] 
                border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-300
                bg-card/30 backdrop-blur-sm overflow-hidden group
                ${isDragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30"}
              `}
            >
              <input type="file" className="hidden" accept=".pdf" onChange={handleFileInput} />
              
              <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-secondary/5 opacity-0 group-hover:opacity-100 transition-opacity" />

              <div className="flex flex-col items-center justify-center pt-5 pb-6 relative z-10">
                <div className="w-20 h-20 mb-6 rounded-full bg-primary/10 flex items-center justify-center group-hover:scale-110 group-hover:bg-primary/20 transition-all duration-500">
                  <UploadCloud className="w-10 h-10 text-primary" />
                </div>
                <p className="mb-2 text-xl font-semibold text-foreground">
                  Click to upload <span className="font-normal text-muted-foreground">or drag and drop</span>
                </p>
                <p className="text-sm text-muted-foreground">
                  PDF documents up to 50MB
                </p>
              </div>
            </label>
          </motion.div>
        )}

        {status === "processing" && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-2xl mx-auto"
          >
            <Card className="p-8 border-border/50 bg-card/80 backdrop-blur-xl shadow-2xl shadow-primary/10 overflow-hidden relative">
              {/* Background abstract glow */}
              <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary/20 rounded-full blur-3xl animate-pulse" />
              <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-secondary/20 rounded-full blur-3xl animate-pulse delay-700" />
              
              <div className="relative z-10 flex flex-col items-center">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-6 relative">
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                  <FileText className="w-4 h-4 text-primary absolute bottom-4 right-4" />
                </div>
                
                <h3 className="text-2xl font-bold mb-2">Analyzing Document</h3>
                <p className="text-muted-foreground mb-8">{file?.name || "financial_report.pdf"}</p>

                <div className="w-full space-y-2 mb-8">
                  <Progress value={progress} className="h-2 w-full bg-muted" />
                  <div className="flex justify-between text-xs text-muted-foreground font-mono">
                    <span>{Math.round(progress)}%</span>
                    <span>100%</span>
                  </div>
                </div>

                <div className="w-full space-y-4">
                  {processingSteps.map((step, idx) => {
                    const isCompleted = idx < currentStepIndex;
                    const isCurrent = idx === currentStepIndex;
                    const StepIcon = step.icon;

                    return (
                      <div
                        key={step.id}
                        className={`flex items-center gap-4 p-3 rounded-xl transition-all duration-500 ${
                          isCurrent ? "bg-primary/10 border border-primary/20 scale-105" : 
                          isCompleted ? "opacity-60" : "opacity-30 grayscale hidden md:flex"
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          isCompleted ? "bg-emerald-500/20 text-emerald-500" :
                          isCurrent ? "bg-background shadow-lg shadow-primary/20" : "bg-muted"
                        }`}>
                          {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : <StepIcon className={`w-4 h-4 ${isCurrent ? step.color : ""}`} />}
                        </div>
                        <span className={`font-medium ${isCurrent ? "text-foreground" : "text-muted-foreground"}`}>
                          {step.text}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </Card>
          </motion.div>
        )}

        {status === "error" && (
           <motion.div
           key="error"
           initial={{ opacity: 0, scale: 0.8 }}
           animate={{ opacity: 1, scale: 1 }}
           className="flex flex-col items-center justify-center h-[400px]"
         >
           <div className="w-24 h-24 rounded-full bg-rose-500/20 flex items-center justify-center mb-6 relative">
             <ShieldCheck className="w-12 h-12 text-rose-500" />
           </div>
           <h2 className="text-3xl font-bold mb-2 text-rose-500">Analysis Failed</h2>
           <p className="text-muted-foreground">{errorMsg}</p>
           <button onClick={() => setStatus("idle")} className="mt-6 px-4 py-2 bg-muted hover:bg-muted/80 rounded-md">Try Again</button>
         </motion.div>
        )}

        {status === "success" && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center h-[400px]"
          >
            <div className="w-24 h-24 rounded-full bg-emerald-500/20 flex items-center justify-center mb-6 relative">
              <div className="absolute inset-0 rounded-full border-4 border-emerald-500/30 animate-ping" />
              <CheckCircle2 className="w-12 h-12 text-emerald-500" />
            </div>
            <h2 className="text-3xl font-bold mb-2">Analysis Complete!</h2>
            <p className="text-muted-foreground">Redirecting to dashboard...</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
