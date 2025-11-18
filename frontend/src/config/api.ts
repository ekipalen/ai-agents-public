// Shared API configuration

export const orchestratorIp = import.meta.env.VITE_ORCHESTRATOR_IP || 'localhost';
export const orchestratorPort = 9000;

/**
 * Helper function to build API URLs
 * @param path - API path starting with /
 * @returns Full API URL
 */
export const getApiUrl = (path: string): string => {
  return `http://${orchestratorIp}:${orchestratorPort}${path}`;
};

/**
 * Helper function to build WebSocket URLs
 * @param path - WebSocket path starting with /
 * @returns Full WebSocket URL
 */
export const getWsUrl = (path: string): string => {
  return `ws://${orchestratorIp}:${orchestratorPort}${path}`;
};
