import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const reportService = {
  uploadReport: async (file: File) => {
    // The backend uses company_id as a Form field and file as a File field
    const formData = new FormData();
    formData.append('file', file);
    formData.append('company_id', '1'); // For demo purposes, mapping to first company
    
    return api.post('/reports/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  
  getReports: async () => {
    return api.get('/reports/');
  },
  
  getReportById: async (id: string | number) => {
    return api.get(`/reports/${id}`);
  },
  
  deleteReport: async (id: string | number) => {
    return api.delete(`/reports/${id}`);
  },
  
  getReportAnalysis: async (id: string | number) => {
    return api.post('/analysis/', {
        report_id: Number(id),
        forecast_days: 90
    });
  },
  
  calculateRatios: async (id: string | number) => {
    return api.post(`/reports/${id}/calculate-ratios`);
  },
  
  getDashboardStats: async () => {
    return api.get('/dashboard/stats');
  },
  
  predictRisk: async (data: any) => {
    return api.post('/ml/risk/', data);
  },
  
  predictFraud: async (text: string) => {
    return api.post('/ml/fraud/', { text });
  },
  
  predictForecast: async (history: any[], days: number = 30) => {
    return api.post('/ml/forecast/', { history, days });
  },
  
  getHealth: async () => {
    return api.get('/health/');
  }
};

export default api;
