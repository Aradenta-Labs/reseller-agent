"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Image as ImageIcon,
  X,
  Coins,
  Square,
} from "lucide-react";

interface ChatInputProps {
  onSubmit: (payload: {
    text: string;
    imageBase64?: string;
    capitalCost?: number;
  }) => void;
  isLoading: boolean;
  onStop?: () => void;
  placeholder?: string;
}

export function ChatInput({
  onSubmit,
  isLoading,
  onStop,
  placeholder = "Describe thrift find or secondhand item (e.g. 'Vintage Nike Windbreaker 90s size L')...",
}: ChatInputProps) {
  const [text, setText] = useState("");
  const [capitalCost, setCapitalCost] = useState<string>("");
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [showCostInput, setShowCostInput] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
      )}px`;
    }
  }, [text]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("Please select a valid image file.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setImagePreview(result);
      const base64Data = result.split(",")[1];
      setImageBase64(base64Data);
    };
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    setImageBase64(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isLoading) return;

    const trimmed = text.trim();
    if (!trimmed && !imageBase64) return;

    let parsedCost: number | undefined = undefined;
    if (capitalCost.trim()) {
      const rawNum = parseFloat(capitalCost.replace(/[^0-9.]/g, ""));
      if (!isNaN(rawNum) && rawNum > 0) {
        parsedCost = rawNum;
      }
    }

    onSubmit({
      text: trimmed,
      imageBase64: imageBase64 || undefined,
      capitalCost: parsedCost,
    });

    // Reset input fields
    setText("");
    removeImage();
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="relative w-full rounded-2xl border border-zinc-800 bg-[#0d0f17] p-3 shadow-lg focus-within:border-zinc-700 transition-all"
    >
      {/* Thumbnail Preview if attached */}
      {imagePreview && (
        <div className="mb-2.5 flex items-center gap-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 p-2">
          <div className="relative h-14 w-14 overflow-hidden rounded-md border border-zinc-700 bg-black shrink-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imagePreview}
              alt="Item preview"
              className="h-full w-full object-cover"
            />
            <button
              type="button"
              onClick={removeImage}
              aria-label="Remove image"
              className="absolute top-0.5 right-0.5 rounded-full bg-black/80 p-0.5 text-zinc-300 hover:text-white"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          <div className="flex-1 text-xs">
            <span className="font-medium text-zinc-200 block">Thrift Image Attached</span>
            <span className="text-[11px] text-zinc-400">
              Agent will visually analyze brand tag, condition & model
            </span>
          </div>
        </div>
      )}

      {/* Optional Capital Cost Input Bar */}
      {showCostInput && (
        <div className="mb-2 flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-1.5 text-xs text-zinc-300">
          <Coins className="h-3.5 w-3.5 text-amber-400 shrink-0" />
          <span className="text-zinc-400 shrink-0">Capital Cost (IDR):</span>
          <input
            type="text"
            value={capitalCost}
            onChange={(e) => setCapitalCost(e.target.value)}
            placeholder="e.g. 150000"
            className="flex-1 bg-transparent font-mono text-xs text-zinc-100 placeholder-zinc-500 focus:outline-hidden"
          />
          <button
            type="button"
            onClick={() => {
              setCapitalCost("");
              setShowCostInput(false);
            }}
            aria-label="Close cost input"
            className="text-zinc-400 hover:text-zinc-200"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Main Textarea */}
      <div className="relative flex items-start">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={1}
          className="w-full resize-none bg-transparent px-2 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-hidden disabled:opacity-50 leading-relaxed font-sans"
        />
      </div>

      {/* Bottom Controls Bar */}
      <div className="mt-2 flex items-center justify-between border-t border-zinc-800/80 pt-2 text-xs">
        <div className="flex items-center gap-1 sm:gap-2">
          {/* Image Upload Button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            disabled={isLoading}
            className="hidden"
            id="thrift-image-upload"
          />
          <label
            htmlFor="thrift-image-upload"
            className={`flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
              imageBase64
                ? "border-blue-500/60 bg-blue-950/30 text-blue-300"
                : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
            } ${isLoading ? "pointer-events-none opacity-50" : ""}`}
            title="Attach thrift photo for visual appraisal"
          >
            <ImageIcon className="h-3.5 w-3.5 text-blue-400" />
            <span className="hidden sm:inline">
              {imageBase64 ? "Photo Attached" : "Add Image"}
            </span>
          </label>

          {/* Capital Cost Toggle Button */}
          <button
            type="button"
            onClick={() => setShowCostInput(!showCostInput)}
            disabled={isLoading}
            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
              capitalCost || showCostInput
                ? "border-amber-500/60 bg-amber-950/30 text-amber-300"
                : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
            } disabled:opacity-50`}
            title="Specify modal capital cost for profit & fee calculations"
          >
            <Coins className="h-3.5 w-3.5 text-amber-400" />
            <span className="hidden sm:inline">
              {capitalCost ? `Rp ${capitalCost}` : "Capital Cost"}
            </span>
          </button>
        </div>

        {/* Action Button: Submit or Stop */}
        <div className="flex items-center gap-2">
          <span className="hidden md:inline text-[11px] text-zinc-400">
            Shift + Enter for new line
          </span>

          {isLoading ? (
            <button
              type="button"
              onClick={onStop}
              className="flex items-center gap-1.5 rounded-lg bg-rose-600/90 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-rose-500 transition-colors shadow-xs"
            >
              <Square className="h-3 w-3 fill-current" />
              <span>Cancel</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!text.trim() && !imageBase64}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-500 transition-colors disabled:opacity-40 shadow-xs"
            >
              <Send className="h-3.5 w-3.5" />
              <span>Analyze</span>
            </button>
          )}
        </div>
      </div>
    </form>
  );
}
