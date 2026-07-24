/**
 * Application Constants
 */

export const MAX_FILE_SIZE = 16 * 1024 * 1024; // 16MB

export const ALLOWED_TYPES = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
  'application/msword': '.doc',
  'text/csv': '.csv',
  'application/vnd.ms-excel': '.csv',
  'text/plain': '.txt'
};

export const ALLOWED_EXTENSIONS = ['.xlsx', '.csv', '.pdf', '.docx', '.doc', '.txt'];
