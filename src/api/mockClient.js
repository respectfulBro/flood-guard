const mockAreas = [
  {
    id: "1",
    name: "Kibera",
    country: "Kenya",
    region: "Nairobi County",
    lat: -1.3125,
    lng: 36.7875,
    risk_tier: "high",
    confidence: "high",
    time_window: "Next 24-48h",
    updated_date: new Date().toISOString()
  },
  {
    id: "2",
    name: "Makoko",
    country: "Nigeria",
    region: "Lagos State",
    lat: 6.4855,
    lng: 3.3815,
    risk_tier: "high",
    confidence: "medium",
    time_window: "Next 48-72h",
    updated_date: new Date().toISOString()
  },
  {
    id: "3",
    name: "Kamukunji",
    country: "Kenya",
    region: "Nairobi County",
    lat: -1.2765,
    lng: 36.8325,
    risk_tier: "moderate",
    confidence: "high",
    time_window: "Next 72h",
    updated_date: new Date().toISOString()
  },
  {
    id: "4",
    name: "Alexandra",
    country: "South Africa",
    region: "Gauteng",
    lat: -26.1075,
    lng: 28.0975,
    risk_tier: "moderate",
    confidence: "medium",
    time_window: "Next 72h",
    updated_date: new Date().toISOString()
  },
  {
    id: "5",
    name: "Soweto",
    country: "South Africa",
    region: "Gauteng",
    lat: -26.2675,
    lng: 27.8550,
    risk_tier: "low",
    confidence: "high",
    time_window: "Next 7 days",
    updated_date: new Date().toISOString()
  },
  {
    id: "6",
    name: "Mathare",
    country: "Kenya",
    region: "Nairobi County",
    lat: -1.2550,
    lng: 36.8650,
    risk_tier: "high",
    confidence: "high",
    time_window: "Next 24h",
    updated_date: new Date().toISOString()
  },
  {
    id: "7",
    name: "Tandale",
    country: "Tanzania",
    region: "Dar es Salaam",
    lat: -6.8000,
    lng: 39.2500,
    risk_tier: "moderate",
    confidence: "medium",
    time_window: "Next 48-72h",
    updated_date: new Date().toISOString()
  },
  {
    id: "8",
    name: "Kisenyi",
    country: "Uganda",
    region: "Kampala",
    lat: 0.3100,
    lng: 32.5800,
    risk_tier: "moderate",
    confidence: "low",
    time_window: "Next 72h",
    updated_date: new Date().toISOString()
  }
];

const mockAlertHistory = [
  {
    id: "a1",
    area_name: "Kibera",
    region: "Nairobi County",
    country: "Kenya",
    tier: "high",
    sent_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    outcome: "hit",
    lead_time_hours: 36
  },
  {
    id: "a2",
    area_name: "Makoko",
    region: "Lagos State",
    country: "Nigeria",
    tier: "high",
    sent_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    outcome: "miss",
    lead_time_hours: 12
  },
  {
    id: "a3",
    area_name: "Mathare",
    region: "Nairobi County",
    country: "Kenya",
    tier: "high",
    sent_at: new Date(Date.now() - 86400000 * 10).toISOString(),
    outcome: "hit",
    lead_time_hours: 48
  },
  {
    id: "a4",
    area_name: "Alexandra",
    region: "Gauteng",
    country: "South Africa",
    tier: "high",
    sent_at: new Date(Date.now() - 86400000 * 15).toISOString(),
    outcome: "false_alarm",
    lead_time_hours: 24
  },
  {
    id: "a5",
    area_name: "Tandale",
    region: "Dar es Salaam",
    country: "Tanzania",
    tier: "high",
    sent_at: new Date(Date.now() - 86400000 * 20).toISOString(),
    outcome: "pending",
    lead_time_hours: null
  }
];

let mockRegistrations = [];
let mockEventReports = [];

const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms));

const createEntityAPI = (dataArray, entityName) => ({
  list: async (sortBy = "id", limit = 100) => {
    await delay();
    let result = [...dataArray];
    if (sortBy.startsWith("-")) {
      const field = sortBy.slice(1);
      result.sort((a, b) => (b[field] > a[field] ? 1 : -1));
    } else {
      result.sort((a, b) => (a[sortBy] > b[sortBy] ? 1 : -1));
    }
    return result.slice(0, limit);
  },
  get: async (id) => {
    await delay();
    const item = dataArray.find(d => d.id === id);
    if (!item) throw { status: 404, message: `${entityName} not found` };
    return item;
  },
  create: async (data) => {
    await delay();
    const newItem = { ...data, id: `${entityName.toLowerCase()}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}` };
    dataArray.push(newItem);
    return newItem;
  },
  update: async (id, data) => {
    await delay();
    const index = dataArray.findIndex(d => d.id === id);
    if (index === -1) throw { status: 404, message: `${entityName} not found` };
    dataArray[index] = { ...dataArray[index], ...data };
    return dataArray[index];
  },
  delete: async (id) => {
    await delay();
    const index = dataArray.findIndex(d => d.id === id);
    if (index === -1) throw { status: 404, message: `${entityName} not found` };
    dataArray.splice(index, 1);
    return { success: true };
  }
});

export const api = {
  entities: {
    Area: createEntityAPI(mockAreas, "Area"),
    Registration: createEntityAPI(mockRegistrations, "Registration"),
    PostEventReport: createEntityAPI(mockEventReports, "PostEventReport"),
    AlertHistory: createEntityAPI(mockAlertHistory, "AlertHistory")
  },
  integrations: {
    Core: {
      UploadPublicFile: async ({ file }) => {
        await delay(500);
        return { file_url: `https://example.com/uploads/${file.name}` };
      }
    }
  },
  auth: {
    me: async () => {
      await delay();
      const token = localStorage.getItem('auth_token');
      if (!token) throw { status: 401, message: "Not authenticated" };
      return { id: "user_1", email: "user@example.com", role: "user" };
    },
    loginViaEmailPassword: async (email, password) => {
      await delay(500);
      if (email && password) {
        const token = "mock_token_" + Date.now();
        localStorage.setItem('auth_token', token);
        return { user: { id: "user_1", email, role: "user" } };
      }
      throw { status: 401, message: "Invalid credentials" };
    },
    loginWithProvider: async (provider, returnTo) => {
      const token = "mock_token_" + Date.now();
      localStorage.setItem('auth_token', token);
      window.location.href = returnTo || "/";
    },
    logout: async (returnTo) => {
      localStorage.removeItem('auth_token');
      if (returnTo) window.location.href = returnTo;
    },
    redirectToLogin: (returnTo) => {
      window.location.href = `/login?returnTo=${encodeURIComponent(returnTo)}`;
    },
    register: async ({ email, password }) => {
      await delay(500);
      if (email && password) {
        return { success: true, message: "Registration successful. Please verify your email." };
      }
      throw { status: 400, message: "Invalid registration data" };
    },
    verifyOtp: async ({ otpCode }) => {
      await delay(500);
      if (otpCode && otpCode.length === 6) {
        const token = "mock_token_" + Date.now();
        localStorage.setItem('auth_token', token);
        return { access_token: token };
      }
      throw { status: 400, message: "Invalid verification code" };
    },
    resendOtp: async () => {
      await delay(500);
      return { success: true, message: "Verification code resent" };
    },
    resetPasswordRequest: async () => {
      await delay(500);
      return { success: true, message: "If an account exists, a reset link has been sent" };
    },
    resetPassword: async ({ resetToken, newPassword }) => {
      await delay(500);
      if (resetToken && newPassword) {
        return { success: true, message: "Password reset successful" };
      }
      throw { status: 400, message: "Invalid reset token or password" };
    },
    setToken: (token) => {
      localStorage.setItem('auth_token', token);
    }
  },
  app: {
    getPublicSettings: async () => {
      await delay();
      return { id: "app_1", public_settings: {} };
    }
  }
};