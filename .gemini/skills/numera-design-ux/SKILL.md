---
name: numera-design-ux
description: UI/UX design standards for Numera. Use this skill when creating or modifying React components, dashboards, or forms to ensure they adhere to shadcn/ui patterns, the project's color palette, and financial data presentation rules.
---

# Numera Design & UX Standards

This skill ensures visual consistency and high-quality user experience across the Numera frontend.

## 1. Visual Identity & Theme
- **Base Style**: We use a clean, professional, "Enterprise-lite" aesthetic.
- **Color Palette**:
    - **Neutral**: Slate (backgrounds, secondary text).
    - **Positive**: Emerald (revenues, gains, success).
    - **Negative**: Rose/Red (expenses, losses, critical alerts).
    - **Warning**: Amber (pending, warnings).
    - **Primary**: Deep Blue/Slate (`--primary`).
- **Typography**: San-serif (inter), antialiased. Use `font-black` for headers and KPI values to create strong visual hierarchy.

## 2. Component Standards (shadcn/ui)
- **UI Components**: Always use components from `@/components/ui`.
- **Consistency**: 
    - Use `Card` for grouping content.
    - Use `Badge` for status and category tags.
    - Use `Button` with appropriate variants (`default`, `outline`, `ghost`, `destructive`).
- **Icons**: Use `lucide-react`. Maintain consistent stroke width and size (usually `h-4 w-4` for inline, `h-5 w-5` for cards).

## 3. Financial Data Presentation
- **Privacy Mode**: Any sensitive financial amount MUST have the class `amount-blur`. The `UIProvider` handles the global state.
- **Formatting**: Always use `formatCurrency(amount, currency)` from `@/lib/utils`.
- **Alignment**: Currency amounts should generally be right-aligned in tables but centered or left-aligned in KPI cards depending on the layout.
- **Positive/Negative Signs**: Use color coding (Emerald/Rose) for amounts rather than just symbols when possible.

## 4. UX Patterns
- **Responsive Design**: Mobile-first approach. Use hidden/block classes to adapt table views or complex layouts for smaller screens.
- **Feedback**: 
    - Use `sonner` for toast notifications after every mutation (Create/Update/Delete).
    - Show `loading` states (Skeleton or Spinner) during data fetching.
- **Navigation**: Keep the sidebar for main navigation and use tabs within pages to separate sub-sections (e.g., in Settings or Dashboard).
- **Omnibox**: Ensure new features are discoverable via the Omnibox (`Command+K`).

## 5. Layout Grid
- **Spacing**: Use standard Tailwind spacing (usually `gap-4` or `gap-6` for grids, `space-y-4` for stacks).
- **Max Width**: Main content containers should use `max-w-7xl` and be centered.
- **Empty States**: Always provide a visual empty state (using an icon and a "Call to Action" button) when a list or chart has no data.
