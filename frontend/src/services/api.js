import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
});

export const analyzeQuery = async (query) => {
  try {
    const response = await api.post('/analyze', { query });
    return response.data;
  } catch (error) {
    console.error('Error in analyzeQuery:', error);
    throw error;
  }
};

export const generateMapData = async (query) => {
  try {
    const response = await api.post('/generate', { query });
    return response.data;
  } catch (error) {
    console.error('Error in generateMapData:', error);
    throw error;
  }
};

export const explainResults = async (data) => {
  try {
    const response = await api.post('/explain', data);
    return response.data;
  } catch (error) {
    console.error('Error in explainResults:', error);
    throw error;
  }
};
