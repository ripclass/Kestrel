"use client";

export function useRealtime(channelName: string) {
  return {
    channelName,
    connected: false,
  };
}
