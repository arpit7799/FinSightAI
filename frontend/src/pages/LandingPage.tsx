import { motion } from "framer-motion";
import { ArrowRight, BarChart3, BrainCircuit, ShieldCheck, Zap, Database, Search, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: <BrainCircuit className="h-6 w-6 text-primary" />,
    title: "AI NLP Analysis",
    description: "Deep semantic understanding of financial reports, extracting key insights and sentiment.",
  },
  {
    icon: <Search className="h-6 w-6 text-accent" />,
    title: "Intelligent OCR",
    description: "Flawlessly digitize and structure data from scanned PDFs and unstructured documents.",
  },
  {
    icon: <ShieldCheck className="h-6 w-6 text-secondary" />,
    title: "Fraud Detection",
    description: "Identify anomalies and potential risks with our advanced machine learning models.",
  },
  {
    icon: <BarChart3 className="h-6 w-6 text-primary" />,
    title: "Predictive Forecasting",
    description: "Forecast future financial performance based on historical data and market trends.",
  },
];

const technologies = [
  "FastAPI", "Python", "React 19", "TensorFlow", "PyTorch", "Tailwind CSS", "SQLAlchemy", "Docker"
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background overflow-hidden selection:bg-primary/30">
      {/* Background gradients */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/20 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-secondary/20 blur-[120px]" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 text-primary font-bold text-2xl tracking-tight">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg shadow-primary/20">
            <span className="text-white text-xl">F</span>
          </div>
          FinSightAI
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#architecture" className="hover:text-foreground transition-colors">Architecture</a>
          <a href="#how-it-works" className="hover:text-foreground transition-colors">How it works</a>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/dashboard">
            <Button variant="ghost" className="hidden sm:inline-flex">Sign In</Button>
          </Link>
          <Link to="/dashboard">
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/20">
              Get Started
            </Button>
          </Link>
        </div>
      </nav>

      <main className="relative z-10">
        {/* Hero Section */}
        <section className="pt-24 pb-32 px-4 text-center max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex flex-col items-center"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-8">
              <Zap className="h-4 w-4" />
              <span>FinSightAI 2.0 is now live</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-foreground mb-8 max-w-4xl">
              AI Powered <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-accent to-secondary">Financial Statement</span> Analysis
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mb-12">
              Transform unstructured financial documents into actionable intelligence. Leverage advanced OCR, NLP, and machine learning to uncover insights, detect fraud, and forecast growth.
            </p>
            <div className="flex items-center gap-4">
              <Link to="/dashboard">
                <Button size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90 h-14 px-8 text-lg rounded-xl shadow-xl shadow-primary/25">
                  Start Analyzing <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="h-14 px-8 text-lg rounded-xl border-border hover:bg-card">
                View Demo
              </Button>
            </div>
          </motion.div>

          {/* Hero Image */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mt-20 relative mx-auto max-w-5xl"
          >
            <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent z-10 rounded-2xl" />
            <div className="rounded-2xl border border-border/50 bg-card/50 backdrop-blur-sm p-2 shadow-2xl relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 to-secondary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <img
                src="/assets/hero_illustration.png"
                alt="AI Financial Dashboard"
                className="w-full h-auto rounded-xl object-cover"
              />
            </div>
          </motion.div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-24 px-4 bg-muted/30 border-y border-border/40">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">Enterprise-Grade Intelligence</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
                Everything you need to automate financial analysis and make data-driven decisions faster than ever.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {features.map((feature, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.1 }}
                  className="bg-card border border-border/50 rounded-2xl p-6 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 group"
                >
                  <div className="w-12 h-12 rounded-xl bg-background border border-border flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Architecture & Tech Stack */}
        <section id="architecture" className="py-24 px-4 max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-3xl md:text-4xl font-bold mb-6">Built on a Modern, Scalable Architecture</h2>
              <p className="text-lg text-muted-foreground mb-8">
                FinSightAI leverages a robust microservices architecture. Our FastAPI backend processes complex machine learning models in real-time, while the React 19 frontend delivers a buttery smooth, premium user experience.
              </p>
              
              <div className="space-y-4 mb-10">
                {[
                  "Secure REST APIs with Swagger documentation",
                  "High-performance Optical Character Recognition",
                  "State-of-the-art NLP for sentiment and risk extraction",
                  "Real-time fraud detection and financial modeling"
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center">
                      <ShieldCheck className="w-3 h-3 text-primary" />
                    </div>
                    <span className="text-foreground font-medium">{item}</span>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                {technologies.map(tech => (
                  <span key={tech} className="px-3 py-1 rounded-full border border-border bg-muted/30 text-sm font-medium">
                    {tech}
                  </span>
                ))}
              </div>
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="relative"
            >
               <div className="absolute inset-0 bg-gradient-to-tr from-accent/20 to-secondary/20 blur-3xl -z-10 rounded-full" />
               <img src="/assets/machine_learning.png" alt="Architecture" className="w-full h-auto rounded-2xl border border-border/50 shadow-2xl" />
            </motion.div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="py-24 px-4 bg-card/30 border-t border-border/40">
          <div className="max-w-7xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-16">How It Works</h2>
            
            <div className="grid md:grid-cols-3 gap-8">
              {[
                { img: "/assets/ocr_processing.png", step: "01", title: "Upload & Extract", desc: "Upload your PDF reports. Our OCR engine instantly extracts structured financial data." },
                { img: "/assets/ai_analysis.png", step: "02", title: "AI Analysis", desc: "NLP and Machine Learning models analyze the data for ratios, risks, and fraud indicators." },
                { img: "/assets/dashboard_preview.png", step: "03", title: "Actionable Insights", desc: "View comprehensive interactive dashboards, forecasts, and download structured reports." }
              ].map((item, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.2 }}
                  className="flex flex-col items-center"
                >
                  <div className="w-full aspect-video rounded-xl overflow-hidden border border-border/50 shadow-lg mb-6 relative group">
                    <img src={item.img} alt={item.title} className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
                    <div className="absolute inset-0 bg-background/20 group-hover:bg-transparent transition-colors" />
                  </div>
                  <div className="w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl mb-4 shadow-lg shadow-primary/30">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-bold mb-2">{item.title}</h3>
                  <p className="text-muted-foreground">{item.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-card py-12 px-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2 text-primary font-bold text-xl tracking-tight">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
              <span className="text-white text-sm">F</span>
            </div>
            FinSightAI
          </div>
          <div className="text-muted-foreground text-sm">
            © 2026 FinSightAI. All rights reserved.
          </div>
          <div className="flex gap-4 text-sm font-medium text-muted-foreground">
            <a href="#" className="hover:text-foreground">Privacy Policy</a>
            <a href="#" className="hover:text-foreground">Terms of Service</a>
            <a href="#" className="hover:text-foreground">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
