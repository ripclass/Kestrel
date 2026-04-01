import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://localhost:8000",
  timeout: 10_000,
});
