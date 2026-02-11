/**
 * Clipboard utility functions for copying text to clipboard.
 */

/**
 * Copy text to clipboard with fallback support.
 * @param text - Text to copy
 * @returns Promise that resolves to true if successful, false otherwise
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  // Check if Clipboard API is available (modern browsers)
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.error("Failed to copy using Clipboard API:", err);
      // Fallback to legacy method
      return fallbackCopyToClipboard(text);
    }
  } else {
    // Fallback to legacy method for older browsers or non-secure contexts
    return fallbackCopyToClipboard(text);
  }
}

/**
 * Fallback method using document.execCommand (for older browsers).
 * @param text - Text to copy
 * @returns true if successful, false otherwise
 */
function fallbackCopyToClipboard(text: string): boolean {
  try {
    // Create a temporary textarea element
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    // Try to copy using execCommand
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);

    return successful;
  } catch (err) {
    console.error("Failed to copy using fallback method:", err);
    return false;
  }
}


