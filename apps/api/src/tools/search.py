"""Web search tool supporting Tavily API, Serper API, and simulated Mock search.

Used primarily by Agent 2 (Trend Analyst) to gather real-time or simulated trends,
recent news, market hype, demand signals, and seasonal relevance for items.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Union
import httpx
from pydantic import BaseModel, Field

from src.models.item import ItemDescription

logger = logging.getLogger("reseller_api.tools.search")


class SearchSnippet(BaseModel):
    """Structured representation of an individual search result snippet."""

    title: str = Field(..., description="Title of the search result page/article")
    snippet: str = Field(..., description="Relevant text excerpt or summary")
    url: str = Field(..., description="Source web link")
    source: Optional[str] = Field(None, description="Domain or publishing source name")
    published_date: Optional[str] = Field(None, description="Published date if available")


class SearchFindings(BaseModel):
    """Structured findings returned by SearchTool."""

    query: str = Field(..., description="Executed search query")
    provider: str = Field(..., description="Search provider used: 'tavily', 'serper', or 'mock'")
    results: List[SearchSnippet] = Field(
        default_factory=list, description="Extracted web snippets and sources"
    )
    trend_signals: List[str] = Field(
        default_factory=list, description="Key trend signals identified from the findings"
    )
    demand_velocity: str = Field(
        "Medium", description="Estimated velocity/demand level: Low, Medium, High"
    )
    summary: str = Field(
        ..., description="Synthesized summary of search findings regarding demand, trends, and hype"
    )


class SearchTool:
    """Multi-provider search tool wrapper supporting Tavily, Serper, and intelligent Mock mode."""

    def __init__(
        self,
        tavily_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
        prefer_provider: Optional[str] = None,
    ):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY")
        self.prefer_provider = prefer_provider

    def _resolve_query(
        self,
        query: Optional[str] = None,
        item: Optional[Union[ItemDescription, Dict[str, Any], str]] = None,
    ) -> str:
        """Resolve a search query from string or item representation."""
        if query and query.strip():
            return query.strip()

        if isinstance(item, ItemDescription):
            features = f" {' '.join(item.key_features)}" if item.key_features else ""
            category = f" {item.category}" if item.category else ""
            return f"{item.name}{features}{category} resale market trend demand Indonesia 2025 2026".strip()

        if isinstance(item, dict):
            name = item.get("name", "")
            summary = item.get("summary", "")
            category = item.get("category", "")
            return f"{name} {category} {summary} trend market demand Indonesia".strip() or "electronics resale trend"

        if isinstance(item, str) and item.strip():
            return f"{item.strip()} trend market demand Indonesia 2025 2026"

        return "trending resale items indonesia demand"

    async def search(
        self,
        query: Optional[str] = None,
        item: Optional[Union[ItemDescription, Dict[str, Any], str]] = None,
        mock: bool = False,
        max_results: int = 5,
    ) -> SearchFindings:
        """Execute a structured web search across Tavily, Serper, or fallback Mock.

        Args:
            query: Direct query string.
            item: ItemDescription or dict/string to build query from.
            mock: If True, forces simulated search response.
            max_results: Maximum snippets to retrieve.

        Returns:
            SearchFindings with structured snippets, sources, and trend signals.
        """
        search_query = self._resolve_query(query=query, item=item)

        if mock:
            logger.info("SearchTool running in explicit mock mode for query: %s", search_query)
            return self._mock_search(search_query, item=item)

        # 1. Try preferred provider or Tavily
        if self.prefer_provider == "serper" and self.serper_api_key:
            findings = await self._search_serper(search_query, max_results=max_results)
            if findings:
                return findings

        if self.tavily_api_key:
            findings = await self._search_tavily(search_query, max_results=max_results)
            if findings:
                return findings

        # 2. Try Serper if Tavily was not available or failed
        if self.serper_api_key and self.prefer_provider != "serper":
            findings = await self._search_serper(search_query, max_results=max_results)
            if findings:
                return findings

        # 3. Graceful Mock Fallback
        logger.info("No active search API keys available or search requests failed; using intelligent Mock search.")
        return self._mock_search(search_query, item=item)

    async def _search_tavily(self, query: str, max_results: int = 5) -> Optional[SearchFindings]:
        """Query Tavily Search API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": True,
                        "max_results": max_results,
                    },
                )
                if response.status_code != 200:
                    logger.warning("Tavily API returned status %s: %s", response.status_code, response.text)
                    return None

                data = response.json()
                results: List[SearchSnippet] = []
                for item in data.get("results", []):
                    results.append(
                        SearchSnippet(
                            title=item.get("title", ""),
                            snippet=item.get("content", ""),
                            url=item.get("url", ""),
                            source=item.get("domain", "") or self._extract_domain(item.get("url", "")),
                            published_date=item.get("published_date"),
                        )
                    )

                trend_signals, demand_velocity = self._infer_signals(query, results)
                summary = data.get("answer") or self._synthesize_summary(query, results, demand_velocity)

                return SearchFindings(
                    query=query,
                    provider="tavily",
                    results=results,
                    trend_signals=trend_signals,
                    demand_velocity=demand_velocity,
                    summary=summary,
                )
        except Exception as e:
            logger.warning("Tavily search failed: %s", str(e))
            return None

    async def _search_serper(self, query: str, max_results: int = 5) -> Optional[SearchFindings]:
        """Query Serper.dev Google Search API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": self.serper_api_key or "",
                        "Content-Type": "application/json",
                    },
                    json={
                        "q": query,
                        "num": max_results,
                    },
                )
                if response.status_code != 200:
                    logger.warning("Serper API returned status %s: %s", response.status_code, response.text)
                    return None

                data = response.json()
                results: List[SearchSnippet] = []
                for item in data.get("organic", [])[:max_results]:
                    results.append(
                        SearchSnippet(
                            title=item.get("title", ""),
                            snippet=item.get("snippet", ""),
                            url=item.get("link", ""),
                            source=self._extract_domain(item.get("link", "")),
                            published_date=item.get("date"),
                        )
                    )

                trend_signals, demand_velocity = self._infer_signals(query, results)
                summary = self._synthesize_summary(query, results, demand_velocity)

                return SearchFindings(
                    query=query,
                    provider="serper",
                    results=results,
                    trend_signals=trend_signals,
                    demand_velocity=demand_velocity,
                    summary=summary,
                )
        except Exception as e:
            logger.warning("Serper search failed: %s", str(e))
            return None

    def _mock_search(
        self,
        query: str,
        item: Optional[Union[ItemDescription, Dict[str, Any], str]] = None,
    ) -> SearchFindings:
        """Intelligent simulated search data generator for testing, demo, and offline fallback."""
        query_lower = query.lower()

        if "iphone" in query_lower or "apple" in query_lower or "macbook" in query_lower:
            demand_velocity = "High"
            trend_signals = [
                "Consistently high search volume on secondhand marketplaces",
                "Strong liquidity with average 3-7 days turnaround time for good condition items",
                "High buyer trust when original box and battery health > 85% are present",
                "Active discussion and price benchmarking across TikTok and forum communities",
            ]
            results = [
                SearchSnippet(
                    title=f"Pasar Bekas {query}: Tren Harga dan Permintaan 2025/2026",
                    snippet=f"Permintaan untuk {query} di pasar secondary Indonesia tetap sangat tinggi. Perputaran unit cepat terutama untuk varian resmi dengan kondisi mulus dan kelengkapan fullset.",
                    url="https://gadget-trend.id/analisis-pasar-second",
                    source="gadget-trend.id",
                    published_date="2025-11-10",
                ),
                SearchSnippet(
                    title=f"Komparasi Nilai Jual Kembali {query} di Tokopedia & Shopee",
                    snippet="Depresiasi harga relatif stabil di kisaran 10-15% per tahun. Peminat cenderung mencari penjual dengan rating tinggi dan opsi COD/rekber.",
                    url="https://techreview.id/resale-value-electronics",
                    source="techreview.id",
                    published_date="2026-01-15",
                ),
                SearchSnippet(
                    title=f"Tips Jual Cepat {query} Tanpa Nego Sadis",
                    snippet="Listing dengan foto detail port, layar, dan battery health biasanya terjual 2x lebih cepat dibanding foto standar marketplace.",
                    url="https://reseller-hub.co.id/tips-jual-gadget",
                    source="reseller-hub.co.id",
                    published_date="2026-02-01",
                ),
            ]
            summary = (
                f"Permintaan pasar untuk '{query}' tergolong High dengan perputaran likuiditas yang cepat. "
                "Produk Apple dan gadget flagship memiliki daya tarik kuat di platform online dan offline. "
                "Faktor kunci penjualan cepat adalah transparansi kondisi fisik, garansi, dan kelengkapan boks."
            )

        elif "sneaker" in query_lower or "jordan" in query_lower or "nike" in query_lower or "adidas" in query_lower or "samba" in query_lower:
            demand_velocity = "High"
            trend_signals = [
                "Viral street style aesthetic driving steady demand",
                "Strong secondary market on Tokopedia and Instagram/Carousell",
                "High sensitivity to authenticity certification and box condition",
                "Popular lifestyle staple with stable price floor",
            ]
            results = [
                SearchSnippet(
                    title=f"Tren Sneakers Indonesia: Demand untuk {query}",
                    snippet=f"Model {query} terus menjadi favorit harian kaum urban di kota-kota besar. Permintaan ukuran umum (40-43) sangat tinggi.",
                    url="https://sneakerhead.co.id/trend-sneakers-2025",
                    source="sneakerhead.co.id",
                    published_date="2025-12-05",
                ),
                SearchSnippet(
                    title="Pasar Preloved Sneakers: Potensi Profit Reselling",
                    snippet="Resale margin berkisar antara 15-25% untuk unit original dengan kondisi 8.5/10 ke atas.",
                    url="https://urbanculture.id/resale-shoes",
                    source="urbanculture.id",
                    published_date="2026-01-20",
                ),
            ]
            summary = (
                f"Analisis tren untuk '{query}' menunjukkan momentum High. "
                "Kategori lifestyle footwear memiliki basis pembeli loyal. "
                "Autentisitas dan bukti pembelian original menjadi syarat mutlak untuk mencapai harga jual optimal."
            )

        elif "sony" in query_lower or "headphone" in query_lower or "audio" in query_lower or "wh-1000" in query_lower:
            demand_velocity = "Medium"
            trend_signals = [
                "Target pembeli niche audio & productivity remote workers",
                "Kebutuhan ANC (Active Noise Canceling) tinggi di kalangan profesional",
                "Kondisi ear pad dan baterai jadi pertimbangan utama pembeli",
            ]
            results = [
                SearchSnippet(
                    title=f"Review Nilai Pakai & Jual {query}",
                    snippet=f"Perangkat audio premium seperti {query} dicari pengguna WFH dan commuter. Depresiasi tahun kedua cenderung melambat.",
                    url="https://audiofile.id/secondhand-audio-guide",
                    source="audiofile.id",
                    published_date="2025-09-12",
                ),
            ]
            summary = (
                f"Kategori audio '{query}' memiliki demand Medium yang stabil. "
                "Target audiens adalah audiophile dan pekerja hybrid. Menampilkan video tes mikrofon dan ANC akan meningkatkan konversi."
            )

        else:
            demand_velocity = "Medium"
            trend_signals = [
                "Volume pencarian stabil di platform e-commerce lokal",
                "Daya saing bergantung pada kompetisi harga dan foto real pict",
                "Pembeli mencari value-for-money dan respon chat cepat",
            ]
            results = [
                SearchSnippet(
                    title=f"Tren Pasar dan Perilaku Pembeli: {query}",
                    snippet=f"Riset pasar terkini menunjukkan minat konsisten terhadap kategori {query} dengan preferensi pengiriman cepat dan gratis ongkir.",
                    url="https://marketinsights.id/consumer-goods-trend",
                    source="marketinsights.id",
                    published_date="2025-10-01",
                ),
                SearchSnippet(
                    title=f"Panduan Pricing Resale {query}",
                    snippet="Memberikan deskripsi transparan mengenai minus produk mempercepat closing transaksi hingga 40%.",
                    url="https://smartreseller.id/pricing-strategy",
                    source="smartreseller.id",
                    published_date="2026-01-10",
                ),
            ]
            summary = (
                f"Hasil pencarian untuk '{query}' menunjukkan tingkat permintaan Medium yang realistis. "
                "Untuk memaksimalkan konversi, disarankan memasang harga kompetitif di bawah median kompetitor dan menyertakan foto kondisi aktual."
            )

        return SearchFindings(
            query=query,
            provider="mock",
            results=results,
            trend_signals=trend_signals,
            demand_velocity=demand_velocity,
            summary=summary,
        )

    def _infer_signals(self, query: str, snippets: List[SearchSnippet]) -> tuple[List[str], str]:
        """Infer trend signals and demand velocity from snippet content."""
        combined_text = " ".join([f"{s.title} {s.snippet}" for s in snippets]).lower()

        signals = []
        if any(w in combined_text for w in ["viral", "trending", "populer", "hype", "laris", "terlaris", "rebutan"]):
            signals.append("Terdapat sinyal popularitas tinggi dan buzz di media sosial/marketplace")
        if any(w in combined_text for w in ["naik", "peningkatan", "growth", "high demand", "permintaan tinggi"]):
            signals.append("Data pasar menunjukkan kurva permintaan positif")
        if any(w in combined_text for w in ["stabil", "konsisten", "steady"]):
            signals.append("Permintaan stabil dengan basis pengguna reguler")
        if any(w in combined_text for w in ["turun", "diskon besar", "obral", "lesu", "oversupply"]):
            signals.append("Pasar cenderung jenuh atau mengalami oversupply")

        if not signals:
            signals.append("Volume pencarian teratur dengan kompetisi moderat di e-commerce")

        # Velocity heuristic
        if any(w in combined_text for w in ["viral", "hype", "high demand", "laris"]):
            velocity = "High"
        elif any(w in combined_text for w in ["turun", "lesu", "sulit", "oversupply"]):
            velocity = "Low"
        else:
            velocity = "Medium"

        return signals, velocity

    def _synthesize_summary(self, query: str, snippets: List[SearchSnippet], velocity: str) -> str:
        """Synthesize natural language summary from retrieved snippets."""
        if not snippets:
            return f"Tidak ditemukan referensi tren eksternal untuk '{query}'. Estimasi permintaan: {velocity}."

        top_titles = [f"'{s.title}'" for s in snippets[:2] if s.title]
        ref_text = f" berdasarkan referensi dari {', '.join(top_titles)}" if top_titles else ""
        return (
            f"Analisis web search untuk '{query}' menunjukkan tingkat demand {velocity}{ref_text}. "
            f"Ditemukan {len(snippets)} sumber informasi relevan mengenai pasar dan perilaku konsumen."
        )

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain name from URL."""
        if not url:
            return "web"
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else "web"
