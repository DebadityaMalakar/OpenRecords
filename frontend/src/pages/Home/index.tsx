import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";

import { useAuthStore } from "@/lib/store/auth";
import ThemeToggle from "@/components/ThemeToggle";

type RecordItem = {
	id: string;
	user_id: string;
	name: string;
	description?: string | null;
	created_at: string;
	updated_at: string;
	last_opened?: string | null;
	chat_model?: string | null;
	embed_model?: string | null;
	doc_count?: number;
};

type RecordsCache = {
	updatedAt: number;
	records: RecordItem[];
};

const CACHE_KEY = "openrecords-records-cache";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

const API_BASE_URL = "/api";

function timeAgo(iso: string): string {
	const then = new Date(iso).getTime();
	if (Number.isNaN(then)) return "just now";
	const diff = Date.now() - then;
	const mins = Math.floor(diff / 60000);
	if (mins < 1) return "just now";
	if (mins < 60) return `${mins}m ago`;
	const hours = Math.floor(mins / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	return `${days}d ago`;
}

export default function Home() {
	const router = useRouter();
	const { user, loadUser, signout } = useAuthStore();
	const [records, setRecords] = useState<RecordItem[]>([]);
	const [search, setSearch] = useState("");
	const [debouncedSearch, setDebouncedSearch] = useState("");
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [menuOpen, setMenuOpen] = useState(false);
	const [selectedIndex, setSelectedIndex] = useState(0);
	const searchRef = useRef<HTMLInputElement>(null);
	const menuRef = useRef<HTMLDivElement>(null);

	const filteredRecords = useMemo(() => {
		const query = debouncedSearch.trim().toLowerCase();
		if (!query) return records;
		return records.filter((record) => {
			const name = record.name.toLowerCase();
			const description = (record.description || "").toLowerCase();
			return name.includes(query) || description.includes(query);
		});
	}, [records, debouncedSearch]);

	useEffect(() => {
		const timer = setTimeout(() => setDebouncedSearch(search), 300);
		return () => clearTimeout(timer);
	}, [search]);

	useEffect(() => {
		const cached = localStorage.getItem(CACHE_KEY);
		if (!cached) return;
		try {
			const parsed: RecordsCache = JSON.parse(cached);
			if (Date.now() - parsed.updatedAt < CACHE_TTL_MS) {
				setRecords(parsed.records || []);
				setIsLoading(false);
			}
		} catch {
			localStorage.removeItem(CACHE_KEY);
		}
	}, []);

	useEffect(() => {
		const syncUserAndData = async () => {
			// If no user in store yet, try to restore session from cookie
			let currentUser = useAuthStore.getState().user;
			if (!currentUser) {
				await loadUser();
				currentUser = useAuthStore.getState().user;
			}

			if (!currentUser) {
				router.push("/login");
				return;
			}

			try {
				setIsLoading(true);
				const response = await fetch(`${API_BASE_URL}/records`, {
					credentials: "include",
				});

				const data = await response.json();
				if (!response.ok) {
					throw new Error(data.detail || "Failed to load records");
				}

				const nextRecords = data.records || [];
				setRecords(nextRecords);
				localStorage.setItem(
					CACHE_KEY,
					JSON.stringify({ updatedAt: Date.now(), records: nextRecords })
				);
				setError(null);
			} catch (err) {
				const message = err instanceof Error ? err.message : "Failed to load records";
				setError(message);
			} finally {
				setIsLoading(false);
			}
		};

		void syncUserAndData();
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	useEffect(() => {
		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.ctrlKey && event.key.toLowerCase() === "k") {
				event.preventDefault();
				searchRef.current?.focus();
			}

			if (event.ctrlKey && event.key.toLowerCase() === "n") {
				event.preventDefault();
				void handleCreateNotebook();
			}

			if (event.ctrlKey && event.key.toLowerCase() === "r") {
				event.preventDefault();
				void refreshRecords();
			}

			if (event.key === "ArrowDown") {
				setSelectedIndex((prev) => Math.min(prev + 1, filteredRecords.length - 1));
			}

			if (event.key === "ArrowUp") {
				setSelectedIndex((prev) => Math.max(prev - 1, 0));
			}

			if (event.key === "Enter" && filteredRecords[selectedIndex]) {
				event.preventDefault();
				const record = filteredRecords[selectedIndex];
				router.push(`/Records/user${record.user_id}/${record.id}`);
			}

			if (event.key === "Escape") {
				setMenuOpen(false);
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [filteredRecords, router, selectedIndex]);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
				setMenuOpen(false);
			}
		};

		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, []);

	const refreshRecords = async () => {
		try {
			setIsLoading(true);
			const response = await fetch(`${API_BASE_URL}/records`, {
				credentials: "include",
			});
			const data = await response.json();
			if (!response.ok) {
				throw new Error(data.detail || "Failed to load records");
			}
			const nextRecords = data.records || [];
			setRecords(nextRecords);
			localStorage.setItem(
				CACHE_KEY,
				JSON.stringify({ updatedAt: Date.now(), records: nextRecords })
			);
			setError(null);
		} catch (err) {
			const message = err instanceof Error ? err.message : "Failed to load records";
			setError(message);
		} finally {
			setIsLoading(false);
		}
	};

	const handleCreateNotebook = async () => {
		try {
			setIsLoading(true);
			const response = await fetch(`${API_BASE_URL}/records/init`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				credentials: "include",
				body: JSON.stringify({ name: "Untitled Notebook" }),
			});
			const data = await response.json();
			if (!response.ok) {
				throw new Error(data.detail || "Failed to create notebook");
			}
			router.push(`/Records/user${data.user_id}/${data.id}?new=True`);
		} catch (err) {
			const message = err instanceof Error ? err.message : "Failed to create notebook";
			setError(message);
		} finally {
			setIsLoading(false);
		}
	};

	const handleLogout = async () => {
		await signout();
		router.push("/");
	};

	return (
		<div className="min-h-screen bg-background text-text">
			<header className="fixed top-0 left-0 right-0 z-40 border-b border-border bg-bg-secondary/90 backdrop-blur-md">
				<div className="container mx-auto px-6 py-4 flex items-center justify-between">
					<Link href="/home" className="flex items-center gap-2 font-semibold text-lg">
						<div className="w-8 h-8 bi-gradient rounded-full" />
						<span className="tracking-tight">OpenRecords</span>
					</Link>

					<div className="flex-1 px-6 hidden md:block">
						<div className="relative">
							<input
								ref={searchRef}
								value={search}
								onChange={(event) => setSearch(event.target.value)}
								placeholder="Search your notebooks..."
								className="w-full px-4 py-3 rounded-full bg-bg-tertiary border border-border text-sm text-text focus:outline-none focus:ring-2 focus:ring-blue-soft"
							/>
							<span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-text-muted">
								Ctrl+K
							</span>
						</div>
					</div>

					<div className="flex items-center gap-3">
						<ThemeToggle />
						<button
							type="button"
							onClick={handleCreateNotebook}
							className="hidden md:inline-flex items-center gap-2 px-4 py-2 rounded-full bi-gradient text-white font-semibold"
						>
							+ New Notebook
						</button>

						<div className="relative" ref={menuRef}>
							<button
								type="button"
								onClick={() => setMenuOpen((prev) => !prev)}
								className="w-10 h-10 rounded-full border border-border flex items-center justify-center bg-bg-tertiary"
							>
								<span className="text-sm font-semibold">
									{user?.username?.slice(0, 2)?.toUpperCase() || "ME"}
								</span>
							</button>

							{menuOpen && (
								<div className="absolute right-0 mt-3 w-56 rounded-xl border border-border bg-bg-secondary shadow-lg overflow-hidden">
									<Link
										href="/account/settings"
										className="w-full text-left px-4 py-3 text-sm hover:bg-bg-tertiary block"
									>
										Settings
									</Link>
									<button
										type="button"
										className="w-full text-left px-4 py-3 text-sm hover:bg-bg-tertiary"
									>
										Default AI Model
									</button>
									<button
										type="button"
										className="w-full text-left px-4 py-3 text-sm hover:bg-bg-tertiary"
									>
										Cache Settings
									</button>
									<button
										type="button"
										className="w-full text-left px-4 py-3 text-sm hover:bg-bg-tertiary"
									>
										Export Data
									</button>
									<button
										type="button"
										onClick={handleLogout}
										className="w-full text-left px-4 py-3 text-sm text-red-400 hover:bg-bg-tertiary"
									>
										Logout
									</button>
								</div>
							)}
						</div>
					</div>
				</div>
			</header>

			<main className="pt-28 pb-16 px-6 container mx-auto">
				<div className="flex items-center justify-between mb-6">
					<h1 className="text-2xl font-semibold">Your notebooks</h1>
					<button
						type="button"
						onClick={refreshRecords}
						className="text-sm text-text-muted hover:text-text"
					>
						Refresh
					</button>
				</div>

				<div className="md:hidden mb-6">
					<input
						ref={searchRef}
						value={search}
						onChange={(event) => setSearch(event.target.value)}
						placeholder="Search your notebooks..."
						className="w-full px-4 py-3 rounded-lg bg-bg-tertiary border border-border text-sm text-text focus:outline-none focus:ring-2 focus:ring-blue-soft"
					/>
				</div>

				{error && (
					<div className="mb-6 p-4 rounded-xl border border-red-500/40 bg-red-900/10 text-red-300 flex items-center justify-between">
						<span>{error}</span>
						<button
							type="button"
							onClick={refreshRecords}
							className="text-sm text-red-200 underline"
						>
							Retry
						</button>
					</div>
				)}

				{isLoading ? (
					<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
						{Array.from({ length: 6 }).map((_, index) => (
							<div
								key={`skeleton-${index}`}
								className="h-36 rounded-2xl border border-border bg-bg-secondary animate-pulse"
							/>
						))}
					</div>
				) : filteredRecords.length === 0 ? (
					<div className="flex flex-col items-center justify-center text-center border border-border rounded-2xl p-12 bg-bg-secondary">
						<h2 className="text-xl font-semibold mb-2">
							You have not created any notebooks yet.
						</h2>
						<p className="text-text-muted mb-6">
							Create your first notebook to start building your archive.
						</p>
						<button
							type="button"
							onClick={handleCreateNotebook}
							className="px-5 py-3 rounded-full bi-gradient text-white font-semibold"
						>
							Create Your First Notebook
						</button>
					</div>
				) : (
					<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
						{filteredRecords.map((record, index) => (
							<button
								type="button"
								key={record.id}
								onClick={() =>
									router.push(`/Records/user${record.user_id}/${record.id}`)
								}
								className={`text-left rounded-2xl border p-5 transition-all bg-bg-secondary hover:border-border-strong hover:shadow-lg ${
									index === selectedIndex ? "border-blue-soft" : "border-border"
								}`}
							>
								<div className="flex items-start justify-between gap-4">
									<div>
										<h3 className="text-lg font-semibold mb-2">{record.name}</h3>
										{record.description && (
											<p className="text-sm text-text-muted line-clamp-2">
												{record.description}
											</p>
										)}
									</div>
								</div>
								<div className="mt-4 text-xs text-text-muted">
									{record.doc_count ?? 0} docs · {record.chat_model || "Default"} · {timeAgo(record.last_opened || record.updated_at)}
								</div>
							</button>
						))}
					</div>
				)}
			</main>

			<button
				type="button"
				onClick={handleCreateNotebook}
				className="md:hidden fixed bottom-6 right-6 w-14 h-14 rounded-full bi-gradient text-white text-2xl shadow-lg"
			>
				+
			</button>
		</div>
	);
}
