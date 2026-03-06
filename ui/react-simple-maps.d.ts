declare module "react-simple-maps" {
  import type { ComponentType, ReactNode } from "react";
  export const ComposableMap: ComponentType<{
    projectionConfig?: object;
    children?: ReactNode;
    [key: string]: unknown;
  }>;
  export const Geographies: ComponentType<{
    geography: string;
    children?: (data: { geographies: unknown[] }) => ReactNode;
    [key: string]: unknown;
  }>;
  export const Geography: ComponentType<{
    geography: unknown;
    children?: (data: { geography: unknown }) => ReactNode;
    [key: string]: unknown;
  }>;
  export const ZoomableGroup: ComponentType<{
    center?: [number, number];
    zoom?: number;
    children?: ReactNode;
    [key: string]: unknown;
  }>;
  export const Line: ComponentType<{
    from: [number, number];
    to: [number, number];
    [key: string]: unknown;
  }>;
  export const Marker: ComponentType<{
    coordinates: [number, number];
    children?: ReactNode;
    [key: string]: unknown;
  }>;
}
