/**
 * FE-013-3: AsyncPool - Producer-Consumer Pattern with Concurrency Limit
 * 
 * Maintains a queue of tasks and processes them with a limited number of concurrent workers.
 * Workers automatically pick up the next task when they finish.
 */

export interface AsyncPoolTask<T> {
  data: T;
  priority?: number; // Higher priority = processed first (for affinity scheduling)
}

export interface AsyncPoolOptions {
  concurrency: number; // Maximum number of concurrent workers
  onTaskComplete?: (result: { success: boolean; data: any; error?: string }) => void;
  onTaskStart?: (data: any) => void;
}

/**
 * AsyncPool - Manages concurrent execution of async tasks with a queue
 */
export class AsyncPool<T> {
  private queue: AsyncPoolTask<T>[] = [];
  private running = 0;
  private concurrency: number;
  private onTaskComplete?: (result: { success: boolean; data: any; error?: string }) => void;
  private onTaskStart?: (data: any) => void;
  private isStopped = false;

  constructor(
    private taskProcessor: (data: T) => Promise<{ success: boolean; error?: string }>,
    options: AsyncPoolOptions
  ) {
    this.concurrency = options.concurrency;
    this.onTaskComplete = options.onTaskComplete;
    this.onTaskStart = options.onTaskStart;
  }

  /**
   * Add a task to the queue
   */
  add(task: T, priority?: number): void {
    if (this.isStopped) {
      return;
    }
    this.queue.push({ data: task, priority });
    // Sort by priority (higher priority first)
    if (priority !== undefined) {
      this.queue.sort((a, b) => (b.priority || 0) - (a.priority || 0));
    }
    // Check queue low after adding (in case we just added tasks)
    this.checkQueueLow();
    this.process();
  }

  /**
   * Add multiple tasks to the queue
   */
  addBatch(tasks: T[], priority?: number): void {
    tasks.forEach(task => this.add(task, priority));
  }

  /**
   * Process the queue (automatically called when tasks are added)
   */
  private async process(): Promise<void> {
    // Don't start more workers if we're at the concurrency limit or queue is empty
    while (this.running < this.concurrency && this.queue.length > 0 && !this.isStopped) {
      const task = this.queue.shift();
      if (!task) {
        break;
      }

      this.running++;
      
      // Call onTaskStart before processing
      this.onTaskStart?.(task.data);

      // Process task asynchronously (don't await, let it run in background)
      Promise.resolve()
        .then(() => this.taskProcessor(task.data))
        .then((result) => {
          this.onTaskComplete?.({ ...result, data: task.data });
        })
        .catch((error) => {
          this.onTaskComplete?.({
            success: false,
            data: task.data,
            error: error instanceof Error ? error.message : String(error),
          });
        })
        .finally(() => {
          this.running--;
          // Check if queue is low and trigger callback
          this.checkQueueLow();
          // Continue processing queue
          this.process();
        });
    }
  }

  /**
   * Wait for all tasks to complete
   */
  async wait(): Promise<void> {
    return new Promise((resolve) => {
      const checkComplete = () => {
        if (this.running === 0 && this.queue.length === 0) {
          resolve();
        } else {
          setTimeout(checkComplete, 10);
        }
      };
      checkComplete();
    });
  }

  /**
   * Stop processing new tasks (existing tasks will complete)
   */
  stop(): void {
    this.isStopped = true;
  }

  /**
   * Get current queue length
   */
  getQueueLength(): number {
    return this.queue.length;
  }

  /**
   * Get number of running workers
   */
  getRunningCount(): number {
    return this.running;
  }

  /**
   * Get total pending tasks (queue + running)
   */
  getTotalPending(): number {
    return this.queue.length + this.running;
  }

  /**
   * Check if pool is idle (no running tasks and empty queue)
   */
  isIdle(): boolean {
    return this.running === 0 && this.queue.length === 0;
  }

  /**
   * Set callback for when queue length drops below threshold
   */
  setQueueLowCallback(callback: () => void, threshold: number = 50): void {
    // Store callback and threshold
    (this as any)._queueLowCallback = callback;
    (this as any)._queueLowThreshold = threshold;
  }

  /**
   * Check queue length and trigger callback if needed
   */
  checkQueueLow(): void {
    const callback = (this as any)._queueLowCallback;
    const threshold = (this as any)._queueLowThreshold;
    if (callback && threshold !== undefined && this.queue.length < threshold) {
      callback();
    }
  }
}

