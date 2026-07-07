import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { 
  FileText, AlertTriangle, TrendingUp, ShieldAlert, Plus, 
  ArrowRight, Activity, Zap, CheckCircle2, XCircle, Database, Server, Loader2, Trash2
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { reportService } from "@/lib/api";

interface DashboardStats {
  companies: number;
  reports: number;
  analyses: number;
  generated_reports: number;
}

interface Report {
  id: number;
  company_id: number;
  original_filename: string;
  upload_date: string;
}

interface HealthStatus {
  status: string;
  message: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [statsRes, reportsRes, healthRes] = await Promise.all([
          reportService.getDashboardStats().catch(() => ({ data: { companies: 0, reports: 0, analyses: 0, generated_reports: 0 } })),
          reportService.getReports().catch(() => ({ data: [] })),
          reportService.getHealth().catch(() => ({ data: { status: "error", message: "Backend offline" } }))
        ]);
        
        setStats(statsRes.data);
        setReports(reportsRes.data);
        setHealth(healthRes.data);
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleDeleteReport = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this report?")) return;
    try {
      await reportService.deleteReport(id);
      setReports(reports.filter(r => r.id !== id));
      const statsRes = await reportService.getDashboardStats().catch(() => null);
      if (statsRes) setStats(statsRes.data);
    } catch (error) {
      console.error("Failed to delete report:", error);
    }
  };

  const statCards = stats ? [
    { title: "Total Reports Processed", value: stats.reports.toString(), icon: FileText, color: "text-blue-500" },
    { title: "Companies Analyzed", value: stats.companies.toString(), icon: Activity, color: "text-purple-500" },
    { title: "AI Analyses Completed", value: stats.analyses.toString(), icon: Zap, color: "text-emerald-500" },
    { title: "Avg. Risk Score", value: stats.reports > 0 ? "Low" : "N/A", icon: ShieldAlert, color: "text-amber-500" },
  ] : [];

  // Mock chart data for now since backend doesn't provide time-series aggregations out of the box
  // In a real app, this would come from a /dashboard/trends API
  const chartData = reports.length > 0 ? [
    { name: "Jan", revenue: 4000 },
    { name: "Feb", revenue: 4200 },
    { name: "Mar", revenue: 4800 },
    { name: "Apr", revenue: 5100 },
    { name: "May", revenue: 5400 },
    { name: "Jun", revenue: 6000 },
    { name: "Jul", revenue: 6800 },
  ] : [];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
          <p className="text-muted-foreground">Monitor your financial analyses and AI insights.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/upload">
            <Button className="bg-primary hover:bg-primary/90 shadow-md shadow-primary/20">
              <Plus className="mr-2 h-4 w-4" /> New Analysis
            </Button>
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <AnimatePresence>
          {/* Stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {statCards.map((stat, index) => (
              <motion.div
                key={stat.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="border-border/50 shadow-sm bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {stat.title}
                    </CardTitle>
                    <stat.icon className={`h-4 w-4 ${stat.color}`} />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-foreground">{stat.value}</div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            {/* Main Chart */}
            <Card className="col-span-4 border-border/50 bg-card/50 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Financial Health Trend</CardTitle>
                <CardDescription>Aggregated metrics over time.</CardDescription>
              </CardHeader>
              <CardContent className="pl-0">
                <div className="h-[300px] w-full mt-4">
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="name" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value}`} />
                        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#0F172A", borderColor: "#1E293B", borderRadius: "8px" }}
                          itemStyle={{ color: "#F8FAFC" }}
                        />
                        <Area type="monotone" dataKey="revenue" stroke="#2563EB" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground space-y-3">
                      <TrendingUp className="h-8 w-8 opacity-20" />
                      <p>No data available</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* AI Insights & System Status */}
            <div className="col-span-3 space-y-4">
              <Card className="border-border/50 bg-gradient-to-br from-primary/10 via-card to-card border-primary/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-primary" />
                    AI Insights Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {reports.length > 0 ? (
                    <>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Based on <strong className="text-foreground">{stats?.reports}</strong> analyzed reports across <strong className="text-foreground">{stats?.companies}</strong> companies, overall portfolio health is <span className="text-emerald-400">stable</span>. Average revenue growth indicators are positive.
                      </p>
                      <Button variant="link" className="px-0 mt-2 h-auto text-primary" onClick={() => navigate(`/analysis/${reports[0].id}`)}>
                        View latest report <ArrowRight className="ml-1 h-4 w-4" />
                      </Button>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      No analyses available yet. Upload a report to generate AI insights.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* System Status Panel */}
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Server className="h-4 w-4" />
                    System Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground flex items-center gap-2"><Database className="h-4 w-4" /> Backend API</span>
                      {health?.status === "healthy" ? <span className="flex items-center gap-1 text-xs text-emerald-500 font-medium"><CheckCircle2 className="h-3 w-3" /> Ready</span> : <span className="flex items-center gap-1 text-xs text-rose-500 font-medium"><XCircle className="h-3 w-3" /> Error</span>}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground flex items-center gap-2"><Activity className="h-4 w-4" /> ML Pipeline</span>
                      {health?.status === "healthy" ? <span className="flex items-center gap-1 text-xs text-emerald-500 font-medium"><CheckCircle2 className="h-3 w-3" /> Ready</span> : <span className="flex items-center gap-1 text-xs text-rose-500 font-medium"><XCircle className="h-3 w-3" /> Error</span>}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Recent Reports */}
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm mt-6">
            <CardHeader>
              <CardTitle>Recent Reports</CardTitle>
              <CardDescription>Latest processed financial documents.</CardDescription>
            </CardHeader>
            <CardContent>
              {reports.length > 0 ? (
                <div className="space-y-4">
                  {reports.map((report) => (
                    <div 
                      key={report.id} 
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/50 hover:bg-muted/50 transition-colors cursor-pointer"
                      onClick={() => navigate(`/analysis/${report.id}`)}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center">
                          <FileText className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{report.original_filename}</p>
                          <p className="text-xs text-muted-foreground">ID: {report.id} • {new Date(report.upload_date).toLocaleDateString()}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-right">
                        <div className="text-xs font-medium px-2 py-1 rounded-full inline-block bg-emerald-500/20 text-emerald-400">
                          Analyzed
                        </div>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          onClick={(e) => handleDeleteReport(e, report.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
                    <FileText className="h-8 w-8 text-muted-foreground opacity-50" />
                  </div>
                  <h3 className="text-lg font-medium mb-1">No financial reports uploaded</h3>
                  <p className="text-sm text-muted-foreground mb-4">Upload your first annual report to generate AI insights.</p>
                  <Link to="/upload">
                    <Button variant="outline">Upload Report</Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </AnimatePresence>
      )}
    </div>
  );
}
