"use client";

import React, { useState, useRef, DragEvent, ChangeEvent } from "react";
import {
  Upload,
  X,
  FileText,
  Sparkles,
  Loader2,
  AlertCircle,
  HelpCircle,
} from "lucide-react";

interface ItemParserInputProps {
  onParse: (payload: { text?: string; image_base64?: string }) => Promise<void>;
  isLoading: boolean;
}

const SAMPLE_PROMPTS = [
  "Sony WH-1000XM4 Wireless Noise Cancelling Headphones, Black. Used for 6 months, minor scuff on left earcup, original box & cable included.",
  "iPhone 13 Pro 256GB Sierra Blue, battery health 87%, pristine screen with tempered glass, no charger included.",
  "Vintage Nike ACG Fleece Jacket Size L 1998, 9/10 condition, no tears or stains, all zippers working.",
];

export function ItemParserInput({ onParse, isLoading }: ItemParserInputProps) {
  const [text, setText] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setValidationError(null);
    if (!file.type.startsWith("image/")) {
      setValidationError("Please select a valid image file (PNG, JPEG, WebP).");
      return;
    }

    // Limit to 8MB
    if (file.size > 8 * 1024 * 1024) {
      setValidationError("Image size must be less than 8MB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setImagePreview(result);
      setImageBase64(result);
    };
    reader.readAsDataURL(file);
  };

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleRemoveImage = () => {
    setImagePreview(null);
    setImageBase64(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmedText = text.trim();
    if (!trimmedText && !imageBase64) {
      setValidationError("Please enter an item description or upload an image.");
      return;
    }

    await onParse({
      text: trimmedText || undefined,
      image_base64: imageBase64 || undefined,
    });
  };

  return (
    <div className="w-full rounded-xl border border-zinc-800 bg-[#10121d] p-5 shadow-lg">
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-zinc-100">
            Item Input & Vision Ingestion
          </h3>
        </div>
        <span className="text-[11px] text-zinc-400">
          Accepts text description, photos, or both
        </span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Text Input */}
        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1.5">
            Raw Description / Listing Text
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={isLoading}
            placeholder="Type or paste unstructured item notes, specs, condition, or listing copy..."
            rows={3}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-hidden focus:ring-1 focus:ring-blue-500 disabled:opacity-50 resize-y min-h-[72px]"
          />
        </div>

        {/* Image Dropzone & Preview */}
        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1.5">
            Item Photo (Vision Extraction)
          </label>

          {imagePreview ? (
            <div className="relative flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-950 p-2.5">
              <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-md border border-zinc-800 bg-zinc-900">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={imagePreview}
                  alt="Uploaded Item"
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-zinc-200 truncate">
                  Image attached for vision inspection
                </p>
                <p className="text-[11px] text-zinc-400">
                  Ready to send to multimodal LLM parser
                </p>
              </div>
              <button
                type="button"
                onClick={handleRemoveImage}
                disabled={isLoading}
                className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-rose-400 transition-colors"
                title="Remove image"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center justify-center rounded-lg border border-dashed p-4 text-center cursor-pointer transition-colors ${
                dragActive
                  ? "border-blue-500 bg-blue-950/20 text-blue-300"
                  : "border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-950"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileInputChange}
                className="hidden"
                disabled={isLoading}
              />
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-900 text-zinc-400 mb-2">
                <Upload className="h-4 w-4" />
              </div>
              <p className="text-xs font-medium text-zinc-300">
                Click to upload or drag & drop item image
              </p>
              <p className="text-[11px] text-zinc-400 mt-0.5">
                PNG, JPG, WebP up to 8MB
              </p>
            </div>
          )}
        </div>

        {/* Validation error */}
        {validationError && (
          <div className="flex items-center gap-1.5 rounded-lg border border-amber-800/50 bg-amber-950/30 p-2.5 text-xs text-amber-300">
            <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Sample Prompts & Submit Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
          {/* Quick sample chips */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-zinc-400 flex items-center gap-1">
              <HelpCircle className="h-3 w-3" /> Samples:
            </span>
            {SAMPLE_PROMPTS.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                disabled={isLoading}
                onClick={() => setText(sample)}
                className="rounded border border-zinc-800 bg-zinc-900/60 px-2 py-0.5 text-[10px] text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-colors"
              >
                Sample {idx + 1}
              </button>
            ))}
          </div>

          {/* Action button */}
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-hidden focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Extracting Metadata...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                <span>Parse Structured Item</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
