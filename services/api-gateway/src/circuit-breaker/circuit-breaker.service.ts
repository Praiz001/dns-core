import { Injectable, Logger } from '@nestjs/common';

export enum CircuitState {
  CLOSED = 'closed', // Normal operation
  OPEN = 'open', // Failing, reject requests
  HALF_OPEN = 'half_open', // Testing if service recovered
}

interface CircuitBreakerConfig {
  failureThreshold: number; // Open circuit after N failures
  resetTimeout: number; // Time before attempting half-open (ms)
  successThreshold: number; // Close circuit after N successes in half-open
}

@Injectable()
export class CircuitBreakerService {
  private readonly logger = new Logger(CircuitBreakerService.name);
  private circuits = new Map<
    string,
    {
      state: CircuitState;
      failures: number;
      successes: number;
      lastFailureTime: number;
      config: CircuitBreakerConfig;
    }
  >();

  private defaultConfig: CircuitBreakerConfig = {
    failureThreshold: 5, // Open after 5 failures
    resetTimeout: 60000, // 60 seconds before half-open
    successThreshold: 2, // Close after 2 successes
  };

  async execute<T>(
    serviceName: string,
    operation: () => Promise<T>,
    config?: Partial<CircuitBreakerConfig>,
  ): Promise<T> {
    const circuit = this.getOrCreateCircuit(serviceName, config);
    const currentState = this.getState(serviceName);

    // If circuit is open, check if we should try half-open
    if (currentState === CircuitState.OPEN) {
      const timeSinceLastFailure = Date.now() - circuit.lastFailureTime;
      if (timeSinceLastFailure >= circuit.config.resetTimeout) {
        this.setState(serviceName, CircuitState.HALF_OPEN);
        circuit.successes = 0;
        this.logger.log(`Circuit ${serviceName} moved to HALF_OPEN state`);
      } else {
        throw new Error(
          `Circuit breaker is OPEN for ${serviceName}. Service unavailable.`,
        );
      }
    }

    try {
      const result = await operation();
      this.onSuccess(serviceName);
      return result;
    } catch (error) {
      this.onFailure(serviceName);
      throw error;
    }
  }

  private getOrCreateCircuit(
    serviceName: string,
    config?: Partial<CircuitBreakerConfig>,
  ) {
    if (!this.circuits.has(serviceName)) {
      this.circuits.set(serviceName, {
        state: CircuitState.CLOSED,
        failures: 0,
        successes: 0,
        lastFailureTime: 0,
        config: { ...this.defaultConfig, ...config },
      });
    }
    return this.circuits.get(serviceName)!;
  }

  private getState(serviceName: string): CircuitState {
    return this.circuits.get(serviceName)?.state || CircuitState.CLOSED;
  }

  private setState(serviceName: string, state: CircuitState) {
    const circuit = this.circuits.get(serviceName);
    if (circuit) {
      circuit.state = state;
    }
  }

  private onSuccess(serviceName: string) {
    const circuit = this.circuits.get(serviceName);
    if (!circuit) return;

    circuit.failures = 0;

    if (circuit.state === CircuitState.HALF_OPEN) {
      circuit.successes++;
      if (circuit.successes >= circuit.config.successThreshold) {
        this.setState(serviceName, CircuitState.CLOSED);
        this.logger.log(`Circuit ${serviceName} CLOSED after recovery`);
      }
    }
  }

  private onFailure(serviceName: string) {
    const circuit = this.circuits.get(serviceName);
    if (!circuit) return;

    circuit.failures++;
    circuit.lastFailureTime = Date.now();

    if (circuit.state === CircuitState.HALF_OPEN) {
      // If we fail in half-open, go back to open
      this.setState(serviceName, CircuitState.OPEN);
      this.logger.warn(
        `Circuit ${serviceName} reopened after failure in HALF_OPEN`,
      );
    } else if (
      circuit.state === CircuitState.CLOSED &&
      circuit.failures >= circuit.config.failureThreshold
    ) {
      this.setState(serviceName, CircuitState.OPEN);
      this.logger.error(
        `Circuit ${serviceName} OPENED after ${circuit.failures} failures`,
      );
    }
  }

  getCircuitState(serviceName: string): CircuitState {
    return this.getState(serviceName);
  }
}
