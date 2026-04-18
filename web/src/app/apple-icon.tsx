import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

// iOS strips alpha — this icon must be opaque. Slate #0F1115 background.
export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#0F1115",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg
          width="126"
          height="82"
          viewBox="0 0 254.04 166.3"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fill="#EAE6DA"
            d="M0,0S77.33,47.6,97.22,62.91s7.67,26.19,7.67,26.19c0,0-39.19,35.87-98.85,77.21,45.5-10.26,79.47-20.72,158.24-46.26,.98-.32,1.96-.67,2.92-1.04,9.16-3.51,41.08-14.87,44.81-39.09,1.57-10.21,10.17-17.97,20.5-17.74,10.93,.24,21.52,4.5,21.52,4.5l-16.25-25.94s-14.14-22.43-61.47-18.6c-6.61,.53-13.25,.61-19.86,.1C93.28,17.38,0,0,0,0Z"
          />
          <path
            fill="#FF3823"
            d="M203.51,46.43h-8.06v-2.19h8.06V27.73h2.19v16.51h8.06v2.19h-8.06v15.87h-2.19v-15.87Z"
          />
        </svg>
      </div>
    ),
    size,
  );
}
