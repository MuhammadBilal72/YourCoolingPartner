/**
 * YourCoolingPartner — Design System
 * Premium dark theme with cool blue accents
 */

export const Colors = {
  // Primary palette — cool blue gradient
  primary: '#0EA5E9',
  primaryLight: '#38BDF8',
  primaryDark: '#0284C7',
  primaryMuted: 'rgba(14, 165, 233, 0.15)',

  // Accent — vibrant teal
  accent: '#06D6A0',
  accentLight: '#34D399',
  accentMuted: 'rgba(6, 214, 160, 0.15)',

  // Background layers (dark theme)
  background: '#0B0F1A',
  surface: '#111827',
  surfaceElevated: '#1E293B',
  surfaceHighlight: '#263244',

  // Text hierarchy
  textPrimary: '#F1F5F9',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  textInverse: '#0B0F1A',

  // Status colors
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',
  pending: '#F59E0B',

  // Borders
  border: 'rgba(148, 163, 184, 0.12)',
  borderLight: 'rgba(148, 163, 184, 0.06)',

  // Overlays
  overlay: 'rgba(0, 0, 0, 0.6)',
  glassBg: 'rgba(30, 41, 59, 0.85)',

  // Misc
  white: '#FFFFFF',
  black: '#000000',
  transparent: 'transparent',
};

export const Gradients = {
  primary: ['#0EA5E9', '#06D6A0'] as const,
  header: ['#0B0F1A', '#111827'] as const,
  card: ['#1E293B', '#111827'] as const,
  accent: ['#06D6A0', '#0EA5E9'] as const,
  dark: ['#0B0F1A', '#111827', '#1E293B'] as const,
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 48,
  massive: 64,
};

export const BorderRadius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  full: 9999,
};

export const FontSize = {
  xs: 11,
  sm: 13,
  md: 15,
  lg: 17,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  hero: 40,
};

export const FontWeight = {
  regular: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
  extrabold: '800' as const,
};

export const Shadows = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 8,
  },
  glow: {
    shadowColor: '#0EA5E9',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 6,
  },
};
