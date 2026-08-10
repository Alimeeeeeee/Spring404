export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const TMAP_APP_KEY = import.meta.env.VITE_TMAP_APP_KEY || '';

export const LIBRARIES = ['places', 'geometry'];

export const center = {
  lat: 37.5563,
  lng: 126.9236,
};

export const mapStyle = {
  width: '100%',
  height: '100%',
};

export const NEAR_ROUTE_DISTANCE_METER = 120;
export const HOME_SHEET_HEIGHT = 120;
export const PLACE_SHEET_HEIGHT = 300;
export const ROUTE_SHEET_HEIGHT = 520;

const koreaBounds = {
  minLat: 33,
  maxLat: 39,
  minLng: 124,
  maxLng: 132,
};

export const isInKorea = (position) => {
  return (
    position.lat >= koreaBounds.minLat &&
    position.lat <= koreaBounds.maxLat &&
    position.lng >= koreaBounds.minLng &&
    position.lng <= koreaBounds.maxLng
  );
};

export const getUserAverage = (arr) => {
  if (arr.length === 0) return '0.00';
  const sum = arr.reduce((acc, cur) => acc + Number(cur.user_score || 0), 0);
  return (sum / arr.length).toFixed(2);
};

export const getAiAverage = (arr) => {
  if (arr.length === 0) return '5.00';
  const sum = arr.reduce((acc, cur) => acc + Number(cur.ai_score || 0), 0);
  return (sum / arr.length).toFixed(2);
};

export const getSafetyColor = (score) => {
  if (score >= 4) return '#16a34a';
  if (score >= 2.5) return '#f59e0b';
  return '#ef4444';
};

export const formatMeter = (meter) => {
  if (!meter && meter !== 0) return '-';
  if (meter >= 1000) return `${(meter / 1000).toFixed(1)}km`;
  return `${Math.round(meter)}m`;
};

export const formatSecond = (second) => {
  if (!second && second !== 0) return '-';

  const min = Math.round(second / 60);

  if (min >= 60) {
    const hour = Math.floor(min / 60);
    const rest = min % 60;
    return `${hour}시간 ${rest}분`;
  }

  return `${min}분`;
};

export const handlePlaceIconError = (e) => {
  e.currentTarget.style.display = 'none';

  const fallback = e.currentTarget.nextElementSibling;
  if (fallback) {
    fallback.style.display = 'inline';
  }
};

export const getPinIcon = (color) => {
  return {
    path: 'M12 2C8.14 2 5 5.14 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.86-3.14-7-7-7z',
    fillColor: color,
    fillOpacity: 1,
    strokeColor: '#ffffff',
    strokeWeight: 2,
    scale: 1.9,
    anchor: new window.google.maps.Point(12, 22),
    labelOrigin: new window.google.maps.Point(12, 8.5),
  };
};

export const getMyLocationIcon = () => {
  return {
    path: window.google.maps.SymbolPath.CIRCLE,
    scale: 9,
    fillColor: '#2563eb',
    fillOpacity: 1,
    strokeColor: '#ffffff',
    strokeWeight: 3,
  };
};
