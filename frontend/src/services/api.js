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

export const getLocations = async () => {
  try {
    const response = await api.get('/locations');
    return response.data;
  } catch (error) {
    console.error('Error in getLocations:', error);
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

export const queryChat = async ({ message, chatId }) => {
  try {
    const response = await api.post('/query', {
      message,
      chat_id: chatId || null,
    });
    return response.data;
  } catch (error) {
    console.error('Error in queryChat:', error);
    throw error;
  }
};

export const listChats = async () => {
  try {
    const response = await api.get('/chats');
    return response.data;
  } catch (error) {
    console.error('Error in listChats:', error);
    throw error;
  }
};

export const getChat = async (chatId) => {
  try {
    const response = await api.get(`/chats/${chatId}`);
    return response.data;
  } catch (error) {
    console.error('Error in getChat:', error);
    throw error;
  }
};

export const getLocationInsight = async ({ location, query, conversation }) => {
  try {
    const response = await api.post('/location-insight', {
      location,
      query,
      conversation: conversation || [],
    });
    return response.data;
  } catch (error) {
    console.error('Error in getLocationInsight:', error);
    throw error;
  }
};

export const nlQuery = async ({ question, cityId = 1 }) => {
  const response = await api.post('/nlquery', { question, city_id: cityId });
  return response.data;
};

export const businessEstimate = async ({ businessType, lat, lng, cityId = 1, sizeSqft = null, tier = 'standard' }) => {
  const response = await api.post('/business-estimate', {
    business_type: businessType,
    lat,
    lng,
    city_id: cityId,
    size_sqft: sizeSqft,
    tier,
  });
  return response.data;
};

export const siteEval = async ({ lat, lng, cityId = 1, radiusM = 1500 }) => {
  const response = await api.post('/site-eval', {
    lat,
    lng,
    city_id: cityId,
    radius_m: radiusM,
  });
  return response.data;
};

export const getPropertiesByLocation = async (region, bhk = null) => {
  try {
    const response = await api.post('/properties', {
      region,
      bhk: bhk,
      price_max: null,
    });
    return response.data;
  } catch (error) {
    console.error('Error in getPropertiesByLocation:', error);
    throw error;
  }
};
