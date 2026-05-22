import streamlit as st
import json
import os
import html
from pathlib import Path
from collections import defaultdict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Apple Feedback Analizi",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Tek seferlik CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Arka plan: Gradient */
.stApp { background: linear-gradient(135deg, #f5f5f7 0%, #ffffff 100%); }
.main .block-container { padding: 2rem 2.5rem 4rem; max-width: 1280px; }

/* Metrik kartları: Renk iyileştirmesi */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
    border: 1.5px solid rgba(0,113,227,0.15);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
[data-testid="metric-container"] > div { gap: 2px; }
[data-testid="stMetricLabel"] { font-size: 0.78rem !important; color: #666666 !important; letter-spacing: .02em; font-weight: 500; }
[data-testid="stMetricValue"] { font-size: 1.9rem !important; font-weight: 700 !important; color: #0071E3; }

/* Sekmeler: Modern tasarım */
[data-baseweb="tab-list"] { gap: 6px; background: rgba(229,229,234,0.4); border-radius: 12px; padding: 6px; border: 1px solid rgba(0,0,0,0.05); }
[data-baseweb="tab"] {
    border-radius: 9px !important;
    padding: 7px 20px !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #555555 !important;
    background: transparent !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: linear-gradient(135deg, #0071E3 0%, #0063d1 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(0,113,227,0.3);
}
[data-baseweb="tab-highlight"] { display: none !important; }
[data-baseweb="tab-border"] { display: none !important; }

/* Expander: Renkli border */
[data-testid="stExpander"] > details {
    border: 1.5px solid rgba(0,113,227,0.2) !important;
    border-radius: 14px !important;
    background: linear-gradient(135deg, #ffffff 0%, #fbfcfd 100%) !important;
    margin-bottom: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
[data-testid="stExpander"] summary {
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.75rem 1rem;
    color: #0071E3;
}

/* Plotly container */
[data-testid="stPlotlyChart"] { border-radius: 16px; overflow: hidden; background: #fff; border: 1px solid rgba(0,113,227,0.1); box-shadow: 0 4px 12px rgba(0,0,0,0.04); }

/* Sidebar */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%); border-right: 1px solid rgba(0,113,227,0.1); }

/* Buton: Primary (mavi) */
.stButton > button {
    background: linear-gradient(135deg, #0071E3 0%, #0063d1 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.6rem 1.4rem;
    box-shadow: 0 4px 12px rgba(0,113,227,0.3);
    transition: all 0.2s ease;
}
.stButton > button:hover { 
    background: linear-gradient(135deg, #0063d1 0%, #004fb8 100%);
    box-shadow: 0 6px 20px rgba(0,113,227,0.4);
    transform: translateY(-2px);
}
.stButton > button:active { transform: translateY(0); }

/* Scrollable yorum listesi */
.yorum-list {
    max-height: 400px;
    overflow-y: auto;
    padding-right: 4px;
}
.yorum-item {
    padding: 10px 14px;
    border-radius: 10px;
    background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
    margin-bottom: 6px;
    font-size: 0.875rem;
    line-height: 1.55;
    color: #1d1d1f;
    border-left: 4px solid #0071E3;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}
.yorum-item:nth-child(odd) { background: linear-gradient(135deg, #f5f5f7 0%, #ffffff 100%); border-left-color: #34C759; }

/* Kategori badge: Renkli */
.badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 11px;
    border-radius: 20px;
    background: linear-gradient(135deg, #E8F3FF 0%, #D0E7FF 100%);
    color: #0071E3;
    margin-bottom: 8px;
    box-shadow: 0 2px 4px rgba(0,113,227,0.15);
}

/* Bilgi kutusu: Yeşil tema */
.info-box {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border: 1.5px solid rgba(52,199,89,0.3);
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 0.85rem;
    color: #2d5016;
    box-shadow: 0 4px 12px rgba(52,199,89,0.1);
}

/* Geri bildirim kutusu: Canlı mavi */
.feedback-box {
    background: linear-gradient(135deg, #ffffff 0%, #f0f7ff 100%);
    border: 1.5px solid rgba(0,113,227,0.2);
    border-radius: 16px;
    padding: 16px 18px;
    margin: 14px 0 18px;
    color: #1d1d1f;
    box-shadow: 0 8px 24px rgba(0,113,227,0.12);
}
.feedback-box h4 {
    margin: 0 0 8px 0;
    font-size: 0.96rem;
    font-weight: 700;
    color: #0071E3;
}
.feedback-box p {
    margin: 0;
    line-height: 1.65;
    font-size: 0.92rem;
    color: #2c2c2e;
}
.feedback-chip {
    display: inline-block;
    margin: 6px 6px 0 0;
    padding: 5px 12px;
    border-radius: 999px;
    background: linear-gradient(135deg, #0071E3 0%, #0063d1 100%);
    color: white;
    font-size: 0.74rem;
    font-weight: 700;
    box-shadow: 0 4px 12px rgba(0,113,227,0.25);
}

/* Divider */
hr { border: none; border-top: 2px solid rgba(0,113,227,0.1); margin: 1.5rem 0; }

/* TextInput & SelectBox */
[data-baseweb="input"] { border-radius: 10px !important; border: 1.5px solid rgba(0,113,227,0.15) !important; }
[data-baseweb="select"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


# ── Performans: verileri cache'le ───────────────────────────────────────────

@st.cache_data(ttl=120)
def load_all_feedback(feedback_dir: str) -> dict[str, dict]:
    """
    Tüm feedback JSON dosyalarını bir kerede yükler ve önbelleğe alır.
    Dosya değişene kadar tekrar diskten okumaz.
    """
    data: dict[str, dict] = {}
    for path in sorted(Path(feedback_dir).glob("*_feedback.json")):
        device = path.stem.replace("_feedback", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data[device] = json.load(f)
        except Exception:
            pass
    return data


@st.cache_data(ttl=120)
def load_scraped_csv(csv_path: str) -> pd.DataFrame | None:
    p = Path(csv_path)
    if not p.exists():
        return None
    try:
        return pd.read_csv(p)
    except Exception:
        return None


@st.cache_data
def build_summary(devices_data: dict) -> dict:
    """Genel istatistikleri hesapla — sadece bir kez çalışır."""
    total_comments = 0
    total_clusters = 0
    device_totals: dict[str, int] = {}
    all_problem_counts: dict[str, int] = defaultdict(int)

    for device, clusters in devices_data.items():
        cnt = sum(v.get("sorun_sayısı", len(v.get("yorumlar", []))) for v in clusters.values())
        device_totals[device] = cnt
        total_comments += cnt
        total_clusters += len(clusters)
        for problem, v in clusters.items():
            all_problem_counts[problem] += v.get("sorun_sayısı", len(v.get("yorumlar", [])))

    return {
        "total_comments":    total_comments,
        "total_clusters":    total_clusters,
        "device_totals":     device_totals,
        "all_problem_counts": dict(all_problem_counts),
    }


def yorumlar_html(yorumlar: list, max_chars: int | None = 300) -> str:
    """
    Yorumları TEK BİR HTML bloğu olarak döndür.
    st.write() döngüsü yerine tek st.markdown() → dramatik hız farkı.
    """
    items = []
    for i, y in enumerate(yorumlar):
        text = str(y.get("yorum", y) if isinstance(y, dict) else y)
        if max_chars is not None and len(text) > max_chars:
            display_text = text[:max_chars] + "…"
        else:
            display_text = text
        display = html.escape(display_text)
        items.append(f'<div class="yorum-item"><b>{i+1}.</b> {display}</div>')
    return f'<div class="yorum-list">{"".join(items)}</div>'


def yorumlar_sayfali_gosterim(yorumlar: list, key_prefix: str, page_size: int = 20) -> None:
    toplam = len(yorumlar)
    if toplam == 0:
        st.caption("Yorum bulunamadı.")
        return

    sayfa_sayisi = max(1, (toplam + page_size - 1) // page_size)
    sayfa_key = f"{key_prefix}_page"
    if sayfa_key not in st.session_state:
        st.session_state[sayfa_key] = 1

    cols = st.columns([1, 1, 3])
    if cols[0].button("◀ Önceki", key=f"{key_prefix}_prev", disabled=st.session_state[sayfa_key] <= 1):
        st.session_state[sayfa_key] -= 1
        st.rerun()
    if cols[1].button("Sonraki ▶", key=f"{key_prefix}_next", disabled=st.session_state[sayfa_key] >= sayfa_sayisi):
        st.session_state[sayfa_key] += 1
        st.rerun()

    page = st.session_state[sayfa_key]
    start = (page - 1) * page_size
    end = min(start + page_size, toplam)

    cols[2].caption(f"{toplam:,} yorum · sayfa {page}/{sayfa_sayisi}")
    st.markdown(yorumlar_html(yorumlar[start:end], max_chars=None), unsafe_allow_html=True)

    if toplam > page_size:
        st.caption("Tam metin görünümünde yorumlar sayfa sayfa yüklenir; böylece arayüz takılmadan çalışır.")


def plotly_theme() -> dict:
    return dict(
        font_family="DM Sans",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=24, r=24, t=40, b=24),
    )


_FEEDBACK_HINTS = {
    "Batarya ve Şarj Sorunu": "Pil optimizasyonu, arka plan tüketimi ve şarj kararlılığı iyileştirilebilir.",
    "Performans ve Hız Sorunu": "Performans iyileştirmeleri, takılma azaltımı ve arka plan süreçlerinin optimizasyonu önerilir.",
    "Yazılım ve Güncelleme Sorunu": "Güncelleme sonrası kararlılık, hata düzeltmeleri ve uyumluluk kontrolleri güçlendirilebilir.",
    "Ekran ve Görünüm Sorunu": "Ekran parlaklığı, dokunmatik tepki ve görüntü kararlılığı tarafı iyileştirilebilir.",
    "Kamera Sorunu": "Kamera odak, netlik ve yazılım kararlılığı için geliştirme yapılabilir.",
    "Servis ve Garanti Sorunu": "Servis süreci, onarım süresi ve kullanıcı bilgilendirmesi daha iyi yönetilebilir.",
    "Bağlantı ve Ağ Sorunu": "Wi-Fi, hücresel bağlantı ve ağ geçişleri daha kararlı hale getirilebilir.",
    "Depolama ve Senkronizasyon Sorunu": "Depolama yönetimi, iCloud senkronizasyonu ve veri temizleme akışları iyileştirilebilir.",
    "Ses ve Mikrofon Sorunu": "Ses çıkışı, mikrofon ve arama kalitesi tarafı optimize edilebilir.",
    "Uygulama ve Sistem Sorunu": "Uygulama çökmesi, sistem stabilitesi ve uyumluluk iyileştirilebilir.",
}


def generate_device_feedback(device_name: str, clusters: dict, device_total: int) -> tuple[str, list[str]]:
    """Cihazın sorun gruplarından kısa bir geri bildirim metni üretir."""
    if not clusters or not device_total:
        return (
            f"{device_name} için yeterli veri bulunamadı.",
            [],
        )

    ranked = sorted(
        clusters.items(),
        key=lambda x: x[1].get("sorun_sayısı", len(x[1].get("yorumlar", []))),
        reverse=True,
    )

    top_items = ranked[:3]
    chips = []
    for problem, data in top_items:
        cnt = data.get("sorun_sayısı", len(data.get("yorumlar", [])))
        chips.append(f"{problem} · {cnt}")

    lead_problem = top_items[0][0]
    lead_hint = _FEEDBACK_HINTS.get(lead_problem, "İlgili alanlarda ürün kararlılığı ve kullanıcı deneyimi iyileştirilebilir.")

    text_parts = [f"{device_name}'te kullanıcılar {lead_problem.lower()}'dan yoğun şekilde şikayetçi."]

    if len(top_items) > 1:
        other_problems = [top_items[i][0].lower() for i in range(1, min(len(top_items), 3))]
        if len(other_problems) == 2:
            text_parts.append(f"Bunu takip eden başlıca sorunlar arasında {other_problems[0]} ve {other_problems[1]} yer alıyor.")
        else:
            text_parts.append(f"Bunu takip eden başlıca sorun {other_problems[0]} yer alıyor.")

    text_parts.append(lead_hint)
    text = " ".join(text_parts)

    return text, chips


# ── SAYFA BAŞI ──────────────────────────────────────────────────────────────

feedback_dir = "feedback"

st.markdown(
    '<h1 style="font-size:2rem;font-weight:600;color:#1d1d1f;margin-bottom:.25rem">'
    '🍎 Apple Geri Bildirim Analizi</h1>'
    '<p style="color:#6e6e73;font-size:.9rem;margin-bottom:1.5rem">'
    'Yorumları cihaz ve sorun türüne göre otomatik kümeleme</p>',
    unsafe_allow_html=True,
)

# ── Feedback yükle ──────────────────────────────────────────────────────────

if not Path(feedback_dir).exists():
    st.markdown(
        '<div class="info-box">⚠️ <b>feedback/</b> klasörü bulunamadı.'
        ' Lütfen önce <code>run.py</code> dosyasını çalıştırın.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

devices_data = load_all_feedback(feedback_dir)

if not devices_data:
    st.info("📭 Henüz feedback dosyası yok. Lütfen önce tarama işlemini yapın.")
    st.stop()

summary = build_summary(devices_data)

# ── Üst metrikler ───────────────────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)
c1.metric("Analiz Edilen Cihaz",    len(devices_data))
c2.metric("Toplam Yorum",           f"{summary['total_comments']:,}")
c3.metric("Toplam Kategori",        summary["total_clusters"])
c4.metric("Ort. Yorum / Cihaz",
          f"{summary['total_comments'] // max(len(devices_data), 1):,}")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Sekmeler ────────────────────────────────────────────────────────────────

device_names  = list(devices_data.keys())
display_names = [d.replace("_", " ").title() for d in device_names]

tab_labels = ["📥 Çekilen Yorumlar"] + [f"📱 {n}" for n in display_names] + ["📊 Genel Dağılım"]
tabs = st.tabs(["📥 Çekilen Yorumlar", "📊 Genel Dağılım"])  # simplified tabs to avoid creating many widgets


# ── TAB 0: Çekilen Yorumlar ─────────────────────────────────────────────────

with tabs[0]:
    st.markdown("### Çekilen yorumlar")
    df_raw = load_scraped_csv("data/tum_cekilen_yorumlar.csv")

    if df_raw is None:
        st.markdown(
            '<div class="info-box">📭 Henüz ham veri yok. '
            '<code>run.py</code> çalıştırıldıktan sonra burada görünecek.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(df_raw):,} yorum listeleniyor")
        # st.dataframe → tek sanal tablo, sonsuz döngü yok
        st.dataframe(
            df_raw,
            use_container_width=True,
            height=520,
            hide_index=True,
        )
        csv_bytes = df_raw.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇ CSV indir", csv_bytes, "yorumlar.csv", "text/csv")


# ── Cihaz seçimi: tek seferde tüm sekmeleri oluşturmaktan kaçın ───────────
st.markdown("### Cihaz İncelemesi")
sel_col, info_col = st.columns([3, 1])
selected_device = sel_col.selectbox("Cihaz seçin", options=device_names, format_func=lambda k: k.replace("_", " ").title())

def render_device_view(device_key: str):
    display_name = device_key.replace("_", " ").title()
    clusters: dict = devices_data.get(device_key, {})
    device_total = summary["device_totals"].get(device_key, 0)

    st.markdown(
        f"<h3 style=\"color:#1d1d1f;font-weight:600\">{display_name}</h3>"
        f"<p style=\"color:#6e6e73;font-size:.85rem;margin-top:-.5rem\">{device_total:,} yorum · {len(clusters)} kategori</p>",
        unsafe_allow_html=True,
    )

    if not clusters:
        st.info("Bu cihaz için veri bulunamadı.")
        return

    feedback_text, feedback_chips = generate_device_feedback(display_name, clusters, device_total)

    st.markdown(
        f"""
        <div class="feedback-box">
            <h4>Otomatik geri bildirim</h4>
            <p>{feedback_text}</p>
            <div style="margin-top:10px;">
                {''.join(f'<span class="feedback-chip">{chip}</span>' for chip in feedback_chips)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Pasta grafiği — yalnızca seçilen cihaz için
    pie_labels = list(clusters.keys())
    pie_values = [
        clusters[k].get("sorun_sayısı", len(clusters[k].get("yorumlar", [])))
        for k in pie_labels
    ]

    if len(pie_labels) > 9:
        pairs = sorted(zip(pie_values, pie_labels), reverse=True)
        top_vals  = [v for v, _ in pairs[:8]]
        top_labels = [l for _, l in pairs[:8]]
        other_val  = sum(v for v, _ in pairs[8:])
        if other_val:
            top_vals.append(other_val)
            top_labels.append("Diğer")
        pie_values, pie_labels = top_vals, top_labels

    fig_pie = go.Figure(go.Pie(
        labels=pie_labels,
        values=pie_values,
        hole=0.48,
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value} yorum (%{percent})<extra></extra>",
        marker=dict(colors=px.colors.qualitative.Pastel),
    ))
    fig_pie.update_layout(
        **plotly_theme(),
        showlegend=True,
        legend=dict(font_size=11, orientation="v", x=1.02, y=0.5),
        height=320,
    )
    fig_pie.add_annotation(
        text=f"<b>{device_total}</b><br><span style='font-size:10px'>yorum</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, family="DM Sans"),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Sorun kategorileri**", unsafe_allow_html=False)

    sorted_clusters = sorted(
        clusters.items(),
        key=lambda x: x[1].get("sorun_sayısı", len(x[1].get("yorumlar", []))),
        reverse=True,
    )

    for sorun, data in sorted_clusters:
        cnt      = data.get("sorun_sayısı", len(data.get("yorumlar", [])))
        yorumlar = data.get("yorumlar", [])
        pct      = (cnt / device_total * 100) if device_total else 0
        safe_key = f"{device_key}_{sorun}".replace(" ", "_").replace("/", "_")

        with st.expander(f"{sorun}  —  {cnt} yorum  ({pct:.1f}%)", expanded=False):
            col_a, col_b = st.columns(2)
            col_a.metric("Yorum sayısı", cnt)
            col_b.metric("Oran", f"%{pct:.1f}")

            full_view = st.toggle("Tam metin göster", key=f"{safe_key}_full_view")

            st.markdown("<br>", unsafe_allow_html=True)

            if not yorumlar:
                st.caption("Yorum bulunamadı.")
            elif full_view:
                yorumlar_sayfali_gosterim(yorumlar, key_prefix=safe_key, page_size=20)
            else:
                st.markdown(yorumlar_html(yorumlar), unsafe_allow_html=True)
                if len(yorumlar) > 20:
                    st.caption(f"İlk 300 karakter gösteriliyor · toplam {len(yorumlar)} yorum")

# Başlangıçta yalnızca seçili cihazın detayını göster
render_device_view(selected_device)


# ── SON TAB: Genel Dağılım ──────────────────────────────────────────────────

with tabs[-1]:
    st.markdown("### Genel sorun dağılımı")

    all_probs = summary["all_problem_counts"]
    dev_tots  = summary["device_totals"]

    if not all_probs:
        st.info("Veri yok.")
    else:
        # ── Bar: tüm kategoriler ──────────────────────────────────────────
        df_all = pd.DataFrame(
            sorted(all_probs.items(), key=lambda x: x[1], reverse=True),
            columns=["Sorun Türü", "Yorum Sayısı"],
        )

        fig_bar = px.bar(
            df_all,
            x="Yorum Sayısı",
            y="Sorun Türü",
            orientation="h",
            color="Yorum Sayısı",
            color_continuous_scale=["#e8f4ff", "#007aff"],
            text="Yorum Sayısı",
        )
        fig_bar.update_traces(textposition="outside", textfont_size=11)
        fig_bar.update_layout(
            **plotly_theme(),
            height=max(320, len(df_all) * 36),
            yaxis=dict(autorange="reversed", tickfont_size=11),
            xaxis_title="",
            yaxis_title="",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Bar: cihaz başı yorum ─────────────────────────────────────────
        st.markdown("**Cihaz başına yorum sayısı**")
        df_dev = pd.DataFrame(
            sorted(dev_tots.items(), key=lambda x: x[1], reverse=True),
            columns=["Cihaz", "Yorum Sayısı"],
        )

        fig_dev = px.bar(
            df_dev,
            x="Yorum Sayısı",
            y="Cihaz",
            orientation="h",
            color="Yorum Sayısı",
            color_continuous_scale=["#e8fff1", "#34c759"],
            text="Yorum Sayısı",
        )
        fig_dev.update_traces(textposition="outside", textfont_size=11)
        fig_dev.update_layout(
            **plotly_theme(),
            height=max(300, len(df_dev) * 36),
            yaxis=dict(autorange="reversed", tickfont_size=11),
            xaxis_title="",
            yaxis_title="",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_dev, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Isı haritası: cihaz × kategori ───────────────────────────────
        st.markdown("**Cihaz × Kategori ısı haritası**")

        all_cats     = sorted(all_probs.keys())
        all_devs_list = list(dev_tots.keys())

        heat_data = []
        for dev in all_devs_list:
            row = []
            for cat in all_cats:
                val = devices_data[dev].get(cat, {})
                row.append(val.get("sorun_sayısı", len(val.get("yorumlar", []))) if val else 0)
            heat_data.append(row)

        if heat_data and any(any(r) for r in heat_data):
            fig_heat = go.Figure(go.Heatmap(
                z=heat_data,
                x=all_cats,
                y=all_devs_list,
                colorscale=[[0, "#f2f2f7"], [1, "#007aff"]],
                hovertemplate="<b>%{y}</b><br>%{x}<br>%{z} yorum<extra></extra>",
                showscale=True,
            ))
            fig_heat.update_layout(
                **plotly_theme(),
                height=max(300, len(all_devs_list) * 40),
                xaxis=dict(tickangle=-35, tickfont_size=10),
                yaxis=dict(tickfont_size=10),
            )
            st.plotly_chart(fig_heat, use_container_width=True)


# ── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<p style="font-weight:600;font-size:1rem;color:#1d1d1f">Ayarlar</p>',
        unsafe_allow_html=True,
    )
    st.caption("Veriler 2 dakikada bir yenilenir.")
    if st.button("↺ Şimdi yenile"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption(
        "Bu dashboard Apple ürünlerine ait kullanıcı yorumlarını "
        "AI tabanlı kümeleme ile analiz eder."
    )