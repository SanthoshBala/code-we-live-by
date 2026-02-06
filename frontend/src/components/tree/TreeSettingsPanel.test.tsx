import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { TreeDisplayProvider } from '@/contexts/TreeDisplayContext';
import TreeSettingsPanel from './TreeSettingsPanel';

function wrapper({ children }: { children: React.ReactNode }) {
  return <TreeDisplayProvider>{children}</TreeDisplayProvider>;
}

describe('TreeSettingsPanel', () => {
  it('renders both toggle checkboxes', () => {
    render(<TreeSettingsPanel />, { wrapper });
    expect(screen.getByLabelText('Connector lines')).toBeInTheDocument();
    expect(screen.getByLabelText('Path breadcrumb')).toBeInTheDocument();
  });

  it('toggles connector lines checkbox', async () => {
    const user = userEvent.setup();
    render(<TreeSettingsPanel />, { wrapper });
    const checkbox = screen.getByLabelText(
      'Connector lines'
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    await user.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });

  it('toggles breadcrumb checkbox', async () => {
    const user = userEvent.setup();
    render(<TreeSettingsPanel />, { wrapper });
    const checkbox = screen.getByLabelText(
      'Path breadcrumb'
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    await user.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });
});
