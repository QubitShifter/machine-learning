export class MatPalApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "MatPalApiError";
    this.status = status;
  }
}
