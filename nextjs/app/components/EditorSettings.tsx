/**
 * Editor Settings Component
 *
 * Modal overlay for configuring editor settings.
 */

"use client";

import { TAB_SIZES } from '../config/editorConfig';

interface EditorSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  fontSize: number;
  onIncreaseFontSize: () => void;
  onDecreaseFontSize: () => void;
  tabSize: number;
  onTabSizeChange: (size: number) => void;
  enableAutocomplete: boolean;
  onAutocompleteToggle: (enabled: boolean) => void;
}

export function EditorSettings({
  isOpen,
  onClose,
  fontSize,
  onIncreaseFontSize,
  onDecreaseFontSize,
  tabSize,
  onTabSizeChange,
  enableAutocomplete,
  onAutocompleteToggle
}: EditorSettingsProps) {
  if (!isOpen) return null;

  const handleApply = () => {
    // Settings are applied instantly through callbacks
    onClose();
  };

  return (
    <div className="fixed inset-0 backdrop-blur-sm bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-[#1e1e1e] rounded-lg shadow-xl w-96 border border-gray-700">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-gray-700">
          <h3 className="text-white font-medium">Editor Settings</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Settings Content */}
        <div className="p-6 space-y-6">
          {/* Font Size Control */}
          <div className="space-y-2">
            <label className="block text-gray-300 text-sm">Font Size</label>
            <div className="flex items-center">
              <button
                onClick={onDecreaseFontSize}
                className="bg-[#3d3d3d] hover:bg-gray-600 text-white w-8 h-8 flex items-center justify-center rounded-l"
              >
                −
              </button>
              <div className="bg-[#2d2d2d] text-white px-4 py-1 w-16 text-center">
                {fontSize}px
              </div>
              <button
                onClick={onIncreaseFontSize}
                className="bg-[#3d3d3d] hover:bg-gray-600 text-white w-8 h-8 flex items-center justify-center rounded-r"
              >
                +
              </button>
            </div>
          </div>

          {/* Tab Size */}
          <div className="space-y-2">
            <label className="block text-gray-300 text-sm">Tab Size</label>
            <div className="bg-[#3d3d3d] rounded overflow-hidden">
              <select
                className="bg-[#3d3d3d] text-white w-full p-2 outline-none"
                value={tabSize}
                onChange={(e) => onTabSizeChange(Number(e.target.value))}
              >
                {TAB_SIZES.map(size => (
                  <option key={size} value={size}>
                    {size} spaces
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Autocomplete Toggle */}
          <div className="space-y-2">
            <label className="block text-gray-300 text-sm">Autocomplete</label>
            <div
              className="flex items-center cursor-pointer"
              onClick={() => onAutocompleteToggle(!enableAutocomplete)}
            >
              <div className={`w-10 h-5 rounded-full flex items-center transition-colors duration-200 ease-in-out ${enableAutocomplete ? 'bg-blue-600' : 'bg-gray-600'}`}>
                <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform duration-200 ease-in-out ${enableAutocomplete ? 'translate-x-5' : 'translate-x-1'}`}></div>
              </div>
              <span className="ml-2 text-gray-300 text-sm">
                {enableAutocomplete ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-700 p-4 flex justify-end space-x-3">
          <button
            className="px-4 py-2 rounded text-gray-300 hover:bg-gray-700"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
            onClick={handleApply}
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}
