/**
 * FE-013-5: Retry utility with exponential backoff
 */

export interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number; // Initial delay in milliseconds
  maxDelay?: number; // Maximum delay in milliseconds
  backoffMultiplier?: number; // Multiplier for exponential backoff
  retryable?: (error: any) => boolean; // Function to determine if error is retryable
}

/**
 * Retry a function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 10000,
    backoffMultiplier = 2,
    retryable = () => true,
  } = options;

  let lastError: any;
  let delay = initialDelay;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Check if error is retryable
      if (!retryable(error)) {
        throw error; // Don't retry non-retryable errors
      }

      // Don't retry on last attempt
      if (attempt === maxRetries) {
        break;
      }

      // Wait before retrying (exponential backoff)
      await new Promise(resolve => setTimeout(resolve, delay));
      delay = Math.min(delay * backoffMultiplier, maxDelay);
    }
  }

  throw lastError;
}

/**
 * Check if an error is a network error (retryable)
 */
export function isNetworkError(error: any): boolean {
  if (!error) return false;
  
  // Fetch errors (network failures, timeouts)
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true;
  }

  // HTTP 5xx errors (server errors)
  if (error.status >= 500 && error.status < 600) {
    return true;
  }

  // HTTP 429 (Too Many Requests)
  if (error.status === 429) {
    return true;
  }

  // Network timeout errors
  if (error.name === 'TimeoutError' || error.message?.includes('timeout')) {
    return true;
  }

  return false;
}

/**
 * Check if an error is a file system permission error (non-retryable)
 */
export function isFileSystemPermissionError(error: any): boolean {
  if (!error) return false;

  const errorMessage = error.message?.toLowerCase() || '';
  const errorName = error.name?.toLowerCase() || '';

  // File system permission errors
  if (
    errorName === 'notallowederror' ||
    errorName === 'securityerror' ||
    errorMessage.includes('permission') ||
    errorMessage.includes('not allowed') ||
    errorMessage.includes('security') ||
    errorMessage.includes('文件系统权限') ||
    errorMessage.includes('权限')
  ) {
    return true;
  }

  return false;
}

