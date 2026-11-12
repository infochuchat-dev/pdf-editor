"""
เว็บแอปพลิเคชันสำหรับจัดการและแก้ไขไฟล์ PDF ด้วย Streamlit และ pypdf (Pure Python 100%)
รองรับ:
1. ระบบหลายฟอนต์ (Multi-Font Support): ตรวจจับฟอนต์ของเอกสาร PDF อัตโนมัติ, มีคลังฟอนต์ไทย/อังกฤษให้เลือกหลากหลาย
   (TH Sarabun New, TH Sarabun Bold, TH Sarabun IT9, Leelawadee, Leelawadee Bold, Leelawadee UI, Tahoma)
   และรองรับการอัปโหลดไฟล์ฟอนต์ .ttf เพิ่มเติมได้เอง (เช่น CSChatThai.ttf, Prompt.ttf, Kanit.ttf)
2. เพิ่มข้อความใหม่แบบลากวางด้วยเมาส์ (Interactive Drag & Drop Text on PDF Page) เลือกฟอนต์แยกแต่ละกล่องได้
3. ไฮไลต์ข้อความ (Highlight Text) เลือกสีไฮไลต์ได้ และเพิ่มข้อความต่อท้ายในบรรทัดเดียวกันได้ทันที
4. แก้ไขข้อความภายในหน้า PDF ได้โดยตรง (ทั้งแก้ไขรายบรรทัด และค้นหา/แทนที่)
5. เพิ่มหน้าเปล่า (Blank Page), แทรก/รวมไฟล์ PDF อื่น, ลบหน้าที่ไม่ต้องการ และดูตัวอย่าง PDF (PDF.js Live Preview)
"""

import base64
import html
import io
import json
import os
import re
import struct
from typing import Dict, List, Optional, Tuple
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    TextStringObject,
)


# สีไฮไลต์มาตรฐาน (RGB 0.0 - 1.0)
HIGHLIGHT_COLORS: Dict[str, Tuple[float, float, float]] = {
    "🟨 สีเหลือง (Yellow)": (1.0, 0.95, 0.35),
    "🟩 สีเขียว (Green)": (0.65, 0.98, 0.65),
    "🟦 สีฟ้า (Cyan)": (0.65, 0.93, 1.0),
    "🟪 สีชมพู (Pink)": (1.0, 0.75, 0.88),
    "🟧 สีส้มอ่อน (Orange)": (1.0, 0.84, 0.50),
}

# สีตัวอักษรสำหรับข้อความที่เพิ่มต่อท้ายหรือลากวาง (RGB 0.0 - 1.0)
APPEND_TEXT_COLORS: Dict[str, Tuple[float, float, float]] = {
    "⚫ สีดำ (ตามเอกสารเดิม)": (0.0, 0.0, 0.0),
    "🔴 สีแดง (เน้นข้อความสำคัญ)": (0.82, 0.08, 0.08),
    "🔵 สีน้ำเงิน": (0.05, 0.25, 0.80),
    "🟢 สีเขียวเข้ม": (0.05, 0.50, 0.15),
}

# รายการฟอนต์มาตรฐานที่รองรับ (ค้นหาทั้งในโฟลเดอร์ fonts/ ของโปรเจกต์ และ C:/Windows/Fonts/)
FONT_CATALOG: Dict[str, Dict[str, List[str]]] = {
    "auto": {
        "label": "🔄 อัตโนมัติ (จับคู่ตามฟอนต์เดิมของเอกสาร PDF)",
        "paths": [],
    },
    "CSChatThai": {
        "label": "🔤 CSChatThai (ซีเอส ชาติไทย - ตรงกับใบเสนอราคาต้นฉบับ 100%)",
        "paths": [
            "fonts/CSChatThai.ttf",
            "CSChatThai.ttf",
            "C:/Windows/Fonts/CSChatThai.ttf",
        ],
    },
    "Leelawadee": {
        "label": "🔤 Leelawadee (ลีลาวดี - มีหัวอ่านง่าย)",
        "paths": [
            "fonts/Leelawadee.ttf",
            "C:/Windows/Fonts/leelawad.ttf",
        ],
    },
    "LeelawadeeBold": {
        "label": "🔤 Leelawadee Bold (ลีลาวดี ตัวหนา)",
        "paths": [
            "fonts/LeelawadeeBold.ttf",
            "C:/Windows/Fonts/leelawdb.ttf",
        ],
    },
    "LeelawadeeUI": {
        "label": "🔤 Leelawadee UI (ลีลาวดี UI - ทันสมัย)",
        "paths": [
            "fonts/LeelawadeeUI.ttf",
            "C:/Windows/Fonts/LeelawUI.ttf",
        ],
    },
    "THSarabunNew": {
        "label": "🔤 TH Sarabun New (สารบรรณนิว - เอกสารราชการ/มาตรฐาน)",
        "paths": [
            "fonts/THSarabunNew.ttf",
            "C:/Windows/Fonts/THSarabunNew.ttf",
        ],
    },
    "THSarabun": {
        "label": "🔤 TH Sarabun (สารบรรณ ปกติ)",
        "paths": [
            "fonts/THSarabun.ttf",
            "THSarabun.ttf",
            "C:/Windows/Fonts/THSarabun.ttf",
        ],
    },
    "THSarabunBold": {
        "label": "🔤 TH Sarabun Bold (สารบรรณ ตัวหนา)",
        "paths": [
            "fonts/THSarabunBold.ttf",
            "C:/Windows/Fonts/THSarabun Bold.ttf",
        ],
    },
    "THSarabunIT9": {
        "label": "🔤 TH Sarabun IT๙ (สารบรรณ ไอที 9)",
        "paths": [
            "fonts/THSarabunIT9.ttf",
            "C:/Windows/Fonts/THSarabunIT๙.ttf",
        ],
    },
    "Tahoma": {
        "label": "🔤 Tahoma (ทาโฮมา - ใบเสนอราคา/ใบกำกับภาษี)",
        "paths": [
            "fonts/Tahoma.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
        ],
    },
}


def hex_to_rgb_float(hex_color: str) -> Tuple[float, float, float]:
    """แปลงสี Hex เช่น '#d11414' เป็น RGB (0.0 - 1.0)"""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0.0, 0.0, 0.0)
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


# ---------------------------------------------------------------------------
# ส่วนจัดการหลายฟอนต์ TrueType (Multi-Font Pure Python Parser)
# ---------------------------------------------------------------------------

def parse_ttf_bytes(data: bytes, font_id: str) -> Optional[Dict]:
    """
    วิเคราะห์ข้อมูลไบต์ของไฟล์ฟอนต์ TrueType (.ttf) ด้วย Pure Python (struct)
    ดึงตาราง cmap, head, hhea, hmtx เพื่อคำนวณความกว้างและฝังลงใน PDF
    """
    try:
        if len(data) < 12:
            return None
        num_tables = struct.unpack(">H", data[4:6])[0]
        tables = {}
        for i in range(num_tables):
            tag = data[12 + i * 16 : 16 + i * 16].decode("ascii", errors="ignore")
            checksum, offset, length = struct.unpack(
                ">III", data[16 + i * 16 : 28 + i * 16]
            )
            tables[tag] = (offset, length)

        if not all(k in tables for k in ("cmap", "head", "hhea", "hmtx")):
            return None

        upm = struct.unpack(
            ">H", data[tables["head"][0] + 18 : tables["head"][0] + 20]
        )[0]
        nhm = struct.unpack(
            ">H", data[tables["hhea"][0] + 34 : tables["hhea"][0] + 36]
        )[0]
        hmtx_off = tables["hmtx"][0]
        widths = [
            int(
                round(
                    struct.unpack(">H", data[hmtx_off + 4 * i : hmtx_off + 4 * i + 2])[
                        0
                    ]
                    * 1000.0
                    / upm
                )
            )
            for i in range(nhm)
        ]

        cmap_off = tables["cmap"][0]
        num_sub = struct.unpack(">H", data[cmap_off + 2 : cmap_off + 4])[0]
        sub_off = None
        for i in range(num_sub):
            plat_id, enc_id, rel_off = struct.unpack(
                ">HHI", data[cmap_off + 4 + i * 8 : cmap_off + 12 + i * 8]
            )
            if (plat_id == 3 and enc_id == 1) or plat_id == 0:
                sub_off = cmap_off + rel_off
                if plat_id == 3 and enc_id == 1:
                    break

        if sub_off is None:
            return None

        fmt = struct.unpack(">H", data[sub_off : sub_off + 2])[0]
        if fmt != 4:
            return None

        _, _, seg_count_x2 = struct.unpack(">HHH", data[sub_off + 2 : sub_off + 8])
        seg_count = seg_count_x2 // 2
        end_codes = struct.unpack(
            f">{seg_count}H", data[sub_off + 14 : sub_off + 14 + 2 * seg_count]
        )
        start_codes = struct.unpack(
            f">{seg_count}H",
            data[sub_off + 16 + 2 * seg_count : sub_off + 16 + 4 * seg_count],
        )
        id_deltas = struct.unpack(
            f">{seg_count}h",
            data[sub_off + 16 + 4 * seg_count : sub_off + 16 + 6 * seg_count],
        )
        ro_pos = sub_off + 16 + 6 * seg_count
        id_range_offsets = struct.unpack(
            f">{seg_count}H", data[ro_pos : ro_pos + 2 * seg_count]
        )

        char_to_gid: Dict[int, int] = {}
        for i in range(seg_count):
            sc, ec, delta, ro = (
                start_codes[i],
                end_codes[i],
                id_deltas[i],
                id_range_offsets[i],
            )
            if sc == 0xFFFF:
                continue
            for code in range(sc, ec + 1):
                if ro == 0:
                    gid = (code + delta) & 0xFFFF
                else:
                    glyph_idx_addr = ro_pos + 2 * i + ro + 2 * (code - sc)
                    if glyph_idx_addr + 2 <= len(data):
                        raw_gid = struct.unpack(
                            ">H", data[glyph_idx_addr : glyph_idx_addr + 2]
                        )[0]
                        gid = (raw_gid + delta) & 0xFFFF if raw_gid != 0 else 0
                    else:
                        gid = 0
                if gid != 0:
                    char_to_gid[code] = gid

        clean_name = re.sub(r"[^A-Za-z0-9]", "", font_id) or "CustomFont"
        return {
            "id": font_id,
            "pdf_base_name": f"/{clean_name}",
            "pdf_res_name": f"/FT_{clean_name}",
            "data": data,
            "widths": widths,
            "char_to_gid": char_to_gid,
        }
    except Exception:
        return None


@st.cache_resource
def load_builtin_fonts_catalog() -> Dict[str, Dict]:
    """โหลดฟอนต์มาตรฐานทั้งหมดที่มีอยู่ในโฟลเดอร์ fonts/ หรือในระบบ"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    loaded: Dict[str, Dict] = {}

    for key, info in FONT_CATALOG.items():
        if key == "auto":
            continue
        for rel_or_abs in info["paths"]:
            candidate = (
                rel_or_abs
                if os.path.isabs(rel_or_abs)
                else os.path.join(base_dir, rel_or_abs)
            )
            if os.path.exists(candidate):
                with open(candidate, "rb") as f:
                    parsed = parse_ttf_bytes(f.read(), key)
                if parsed:
                    parsed["label"] = info["label"]
                    loaded[key] = parsed
                    break

    # หากไม่พบฟอนต์ตามรายการ ให้ลองค้นหาไฟล์ .ttf ใดๆ ในโฟลเดอร์โปรเจกต์
    if not loaded:
        fallback_ttf = os.path.join(base_dir, "THSarabun.ttf")
        if os.path.exists(fallback_ttf):
            with open(fallback_ttf, "rb") as f:
                parsed = parse_ttf_bytes(f.read(), "THSarabun")
            if parsed:
                parsed["label"] = "🔤 TH Sarabun"
                loaded["THSarabun"] = parsed

    return loaded


def get_all_available_fonts() -> Dict[str, Dict]:
    """รวมฟอนต์ในตัวโปรแกรมเข้ากับฟอนต์ที่ผู้ใช้อัปโหลดเพิ่มเติมใน Session"""
    catalog = dict(load_builtin_fonts_catalog())
    custom_fonts = st.session_state.get("custom_uploaded_fonts", {})
    for k, v in custom_fonts.items():
        catalog[k] = v
    return catalog


def detect_pdf_fonts(reader: PdfReader) -> List[str]:
    """ตรวจสอบรายชื่อฟอนต์ทั้งหมดที่ฝังอยู่ในไฟล์ PDF ต้นฉบับ"""
    detected = []
    seen = set()
    for page in reader.pages:
        try:
            resources = page.get("/Resources")
            if not resources or "/Font" not in resources:
                continue
            fonts = resources["/Font"].get_object()
            for font_ref in fonts.values():
                font_obj = font_ref.get_object()
                base_font = str(font_obj.get("/BaseFont", "")).lstrip("/")
                if "+" in base_font:
                    base_font = base_font.split("+", 1)[1]
                if base_font and base_font not in seen:
                    seen.add(base_font)
                    detected.append(base_font)
        except Exception:
            pass
    return detected


def resolve_best_font_key(
    requested_key: str,
    detected_fonts: List[str],
    available_fonts: Dict[str, Dict],
) -> str:
    """
    เลือกฟอนต์ที่เหมาะสมที่สุด:
    - หากผู้ใช้ระบุชื่อฟอนต์โดยตรง ให้ใช้ฟอนต์นั้น
    - หากเลือก 'auto' ให้จับคู่กับฟอนต์ที่ตรวจพบในไฟล์ PDF ต้นฉบับโดยอัตโนมัติ
    """
    if requested_key != "auto" and requested_key in available_fonts:
        return requested_key

    # ตรวจสอบจากฟอนต์หลักตัวแรกของเอกสาร (detected_fonts[0]) ก่อนเป็นอันดับแรก
    search_order = (
        [detected_fonts[0].lower(), " ".join(detected_fonts).lower()]
        if detected_fonts
        else [""]
    )

    for target in search_order:
        for k in available_fonts:
            if k.lower() in target:
                return k
        if any(w in target for w in ["chatthai", "cschat"]):
            if "CSChatThai" in available_fonts:
                return "CSChatThai"
        if any(
            w in target
            for w in ["chatthai", "cschat", "leela", "sukhumvit", "kanit", "prompt"]
        ):
            if "Leelawadee" in available_fonts:
                return "Leelawadee"
            if "LeelawadeeUI" in available_fonts:
                return "LeelawadeeUI"
        if any(w in target for w in ["sarabun", "angsana", "cordia", "browa", "upc"]):
            if "THSarabunNew" in available_fonts:
                return "THSarabunNew"
            if "THSarabun" in available_fonts:
                return "THSarabun"
        if any(w in target for w in ["tahoma", "arial", "calibri", "helvetica", "sans"]):
            if "Tahoma" in available_fonts:
                return "Tahoma"

    # ค่าเริ่มต้นหากไม่ตรงกับเงื่อนไขข้างต้น
    for pref in ("Leelawadee", "THSarabunNew", "THSarabun", "Tahoma", "LeelawadeeUI"):
        if pref in available_fonts:
            return pref
    return next(iter(available_fonts.keys()), "")


def embed_selected_font_on_page(
    writer: PdfWriter,
    page: PageObject,
    ttf_info: Dict,
    used_chars: str,
) -> str:
    """
    ฝังฟอนต์ TrueType ที่เลือกลงใน Resources ของหน้า PDF (เช่น /FT_Leelawadee, /FT_THSarabunNew)
    """
    char_to_gid = ttf_info["char_to_gid"]
    widths = ttf_info["widths"]
    base_name = ttf_info["pdf_base_name"]
    res_name = ttf_info["pdf_res_name"]

    font_file_stream = DecodedStreamObject()
    font_file_stream.set_data(ttf_info["data"])
    font_file_ref = writer._add_object(font_file_stream)

    font_descriptor = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/FontDescriptor"),
            NameObject("/FontName"): NameObject(base_name),
            NameObject("/Flags"): NumberObject(32),
            NameObject("/FontBBox"): ArrayObject(
                [
                    NumberObject(-500),
                    NumberObject(-300),
                    NumberObject(1500),
                    NumberObject(1100),
                ]
            ),
            NameObject("/ItalicAngle"): NumberObject(0),
            NameObject("/Ascent"): NumberObject(1000),
            NameObject("/Descent"): NumberObject(-250),
            NameObject("/CapHeight"): NumberObject(700),
            NameObject("/StemV"): NumberObject(80),
            NameObject("/FontFile2"): font_file_ref,
        }
    )
    fd_ref = writer._add_object(font_descriptor)

    w_entries = ArrayObject()
    used_gids = sorted(
        {char_to_gid.get(ord(ch), 0) for ch in used_chars if ord(ch) in char_to_gid}
    )
    for gid in used_gids:
        w_val = widths[gid] if gid < len(widths) else 600
        w_entries.append(NumberObject(gid))
        w_entries.append(ArrayObject([NumberObject(w_val)]))

    descendant_font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/CIDFontType2"),
            NameObject("/BaseFont"): NameObject(base_name),
            NameObject("/CIDSystemInfo"): DictionaryObject(
                {
                    NameObject("/Registry"): TextStringObject("Adobe"),
                    NameObject("/Ordering"): TextStringObject("Identity"),
                    NameObject("/Supplement"): NumberObject(0),
                }
            ),
            NameObject("/FontDescriptor"): fd_ref,
            NameObject("/CIDToGIDMap"): NameObject("/Identity"),
            NameObject("/DW"): NumberObject(600),
            NameObject("/W"): w_entries,
        }
    )
    df_ref = writer._add_object(descendant_font)

    bf_lines = []
    for ch in sorted(set(used_chars)):
        gid = char_to_gid.get(ord(ch))
        if gid:
            bf_lines.append(f"<{gid:04x}> <{ord(ch):04x}>")

    cmap_text = (
        "/CIDInit /ProcSet findresource begin\n"
        "12 dict begin\n"
        "begincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def\n"
        "/CMapType 2 def\n"
        "1 begincodespacerange\n"
        "<0000> <FFFF>\n"
        "endcodespacerange\n"
        f"{len(bf_lines)} beginbfchar\n"
        + "\n".join(bf_lines)
        + "\nendbfchar\n"
        "endcmap\n"
        "CMapName currentdict /CMap defineresource pop\n"
        "end\nend\n"
    )
    tounicode_stream = DecodedStreamObject()
    tounicode_stream.set_data(cmap_text.encode("latin-1"))
    tu_ref = writer._add_object(tounicode_stream)

    type0_font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type0"),
            NameObject("/BaseFont"): NameObject(base_name),
            NameObject("/Encoding"): NameObject("/Identity-H"),
            NameObject("/DescendantFonts"): ArrayObject([df_ref]),
            NameObject("/ToUnicode"): tu_ref,
        }
    )
    font_ref = writer._add_object(type0_font)

    if "/Resources" not in page:
        page[NameObject("/Resources")] = DictionaryObject()
    resources = page["/Resources"].get_object()
    if "/Font" not in resources:
        resources[NameObject("/Font")] = DictionaryObject()
    font_dict = resources["/Font"].get_object()
    font_dict[NameObject(res_name)] = font_ref
    return res_name


# คงฟังก์ชัน load_windows_thai_ttf ไว้เพื่อความเข้ากันได้กับ main.py
def load_windows_thai_ttf() -> Optional[Dict]:
    catalog = load_builtin_fonts_catalog()
    return next(iter(catalog.values()), None)


# ---------------------------------------------------------------------------
# ส่วนอ่านตารางฟอนต์ ความกว้างตัวอักษร และแยกกลุ่มข้อความในหน้า PDF
# ---------------------------------------------------------------------------

def extract_cid_widths(font_obj: DictionaryObject) -> Dict[int, float]:
    """ดึงความกว้างของแต่ละ CID (หน่วย 1/1000 ของขนาดฟอนต์) จากตาราง /W ของฟอนต์ใน PDF"""
    cid_widths: Dict[int, float] = {}
    try:
        if "/DescendantFonts" not in font_obj:
            return cid_widths
        df = font_obj["/DescendantFonts"][0].get_object()
        if "/W" not in df:
            return cid_widths
        w_arr = df["/W"].get_object()
        i = 0
        while i < len(w_arr):
            start_cid = int(w_arr[i])
            next_item = w_arr[i + 1].get_object()
            if isinstance(next_item, ArrayObject):
                for offset, val in enumerate(next_item):
                    cid_widths[start_cid + offset] = float(val)
                i += 2
            else:
                end_cid = int(next_item)
                val = float(w_arr[i + 2])
                for cid in range(start_cid, end_cid + 1):
                    cid_widths[cid] = val
                i += 3
    except Exception:
        pass
    return cid_widths


def repair_page_tounicode(
    page: PageObject,
) -> Dict[str, Tuple[Dict[int, str], Dict[str, int], Dict[int, float]]]:
    """
    ซ่อมแซมตาราง /ToUnicode ที่มีค่าว่าง <> ในไฟล์ PDF ภาษาไทย
    พร้อมคืนค่า (cid_to_char, char_to_cid, cid_widths) ของแต่ละฟอนต์ในหน้านั้น
    """
    font_maps: Dict[str, Tuple[Dict[int, str], Dict[str, int], Dict[int, float]]] = {}
    try:
        resources = page.get("/Resources")
        if not resources or "/Font" not in resources:
            return font_maps
        fonts = resources["/Font"].get_object()
        for font_name, font_ref in fonts.items():
            font_obj = font_ref.get_object()
            if "/ToUnicode" not in font_obj:
                continue
            cmap_obj = font_obj["/ToUnicode"].get_object()
            raw_data = cmap_obj.get_data()
            if b"<>" in raw_data:
                fixed_stream = DecodedStreamObject()
                fixed_stream.set_data(raw_data.replace(b"<>", b"<0e32>"))
                font_obj[NameObject("/ToUnicode")] = fixed_stream

            cmap_str = raw_data.decode("latin-1", errors="ignore")
            cid_to_char: Dict[int, str] = {}
            if "beginbfrange" in cmap_str:
                for section in cmap_str.split("beginbfrange")[1:]:
                    body = section.split("endbfrange")[0]
                    if "[" in body:
                        tokens = re.findall(r"<([0-9a-fA-F]*)>", body)
                        if len(tokens) >= 3:
                            start_cid = int(tokens[0], 16) if tokens[0] else 0
                            for idx, hex_val in enumerate(tokens[2:]):
                                cid = start_cid + idx
                                ch = chr(int(hex_val, 16)) if hex_val else "\u0e32"
                                cid_to_char[cid] = ch
            if "beginbfchar" in cmap_str:
                for section in cmap_str.split("beginbfchar")[1:]:
                    body = section.split("endbfchar")[0]
                    pairs = re.findall(r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]*)>", body)
                    for src_hex, dst_hex in pairs:
                        cid = int(src_hex, 16)
                        ch = chr(int(dst_hex, 16)) if dst_hex else "\u0e32"
                        cid_to_char[cid] = ch

            char_to_cid = {v: k for k, v in cid_to_char.items() if v}
            cid_widths = extract_cid_widths(font_obj)
            font_maps[str(font_name)] = (cid_to_char, char_to_cid, cid_widths)
    except Exception:
        pass
    return font_maps


def match_keyword_in_text(keyword: str, text: str) -> Optional[str]:
    """ค้นหาคำในข้อความของ PDF โดยรองรับทั้งการค้นหาตรงตัว และการค้นหาแบบข้ามช่องว่างพิเศษใน PDF"""
    kw = keyword.strip()
    if not kw:
        return None
    if kw in text:
        return kw
    parts = [re.escape(p) for p in kw.split() if p]
    if len(parts) > 1:
        flex_pattern = r"\s*".join(parts)
        m = re.search(flex_pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def compute_text_width_pt(
    text: str,
    font_size: float,
    char_to_cid: Dict[str, int],
    cid_widths: Dict[int, float],
    ttf_info: Optional[Dict],
) -> float:
    """คำนวณความกว้างของข้อความ (หน่วย Point) อย่างแม่นยำตามตารางความกว้างฟอนต์"""
    if not text:
        return 0.0

    expanded = text
    if "\u0e33" in expanded and "\u0e32" in char_to_cid:
        if "\u0e4d" in char_to_cid:
            expanded = expanded.replace("\u0e33", "\u0e4d\u0e32")
        elif "\u0e33" in char_to_cid:
            expanded = expanded.replace("\u0e33", "\u0e33\u0e32")

    total_w = 0.0
    combining_thai = set(
        "\u0e31\u0e34\u0e35\u0e36\u0e37\u0e38\u0e39\u0e3a\u0e47\u0e48\u0e49\u0e4a\u0e4b\u0e4c\u0e4d\u0e4e"
    )

    for ch in expanded:
        if ch in char_to_cid and char_to_cid[ch] in cid_widths:
            total_w += cid_widths[char_to_cid[ch]]
        elif ttf_info and ord(ch) in ttf_info["char_to_gid"]:
            gid = ttf_info["char_to_gid"][ord(ch)]
            if ch in combining_thai:
                total_w += 0.0
            elif gid < len(ttf_info["widths"]):
                total_w += ttf_info["widths"][gid]
            else:
                total_w += 450.0
        else:
            total_w += 0.0 if ch in combining_thai else 450.0

    return total_w * (font_size / 1000.0)


def parse_page_text_groups(page: PageObject) -> List[Dict]:
    """
    ดึงกลุ่มข้อความ (Text Blocks) จากหน้า PDF พร้อมพิกัดเริ่มต้น (x), พิกัดสิ้นสุด (end_x),
    พิกัดแนวตั้ง (y) และขนาดตัวอักษร
    """
    font_maps = repair_page_tounicode(page)
    contents = page.get_contents()
    if contents is None:
        return []

    raw_stream = contents.get_data().decode("latin-1", errors="ignore")
    pattern = re.compile(
        r"BT\s+1 0 0 1 ([0-9.]+) ([0-9.]+) Tm\s+(/(?:F\d+|FThai|FT_[A-Za-z0-9]+))\s+([0-9.]+) Tf\s+(.*?)\s+ET",
        re.S,
    )

    items = []
    for match in pattern.finditer(raw_stream):
        x = float(match.group(1))
        y = float(match.group(2))
        font_key = match.group(3)
        font_size = float(match.group(4))
        inner_tj = match.group(5)

        cid_to_char, _, cid_widths = font_maps.get(font_key, ({}, {}, {}))
        hex_chunks = re.findall(r"<([0-9a-fA-F]+)>", inner_tj)
        chars = []
        cids = []
        for chunk in hex_chunks:
            for j in range(0, len(chunk), 4):
                code = int(chunk[j : j + 4], 16)
                cids.append(code)
                chars.append(cid_to_char.get(code, ""))

        blk_width = sum(cid_widths.get(c, 450.0) for c in cids) * (font_size / 1000.0)
        text_piece = (
            "".join(chars)
            .replace("\u0e4d\u0e32", "\u0e33")
            .replace("\u0e33\u0e32", "\u0e33")
        )
        items.append(
            {
                "span": match.span(),
                "x": x,
                "end_x": x + blk_width,
                "width": blk_width,
                "y": y,
                "font_key": font_key,
                "font_size": font_size,
                "text": text_piece,
            }
        )

    groups: List[List[Dict]] = []
    for it in items:
        if (
            not groups
            or abs(it["y"] - groups[-1][-1]["y"]) > 2.5
            or abs(it["x"] - groups[-1][-1]["x"]) > 55.0
        ):
            groups.append([it])
        else:
            groups[-1].append(it)

    result = []
    for g in groups:
        combined_text = "".join(x["text"] for x in g)
        if not combined_text.strip():
            continue
        x_start = g[0]["x"]
        x_end = max(b["end_x"] for b in g)
        result.append(
            {
                "x": x_start,
                "end_x": x_end,
                "width": max(x_end - x_start, 8.0),
                "y": g[0]["y"],
                "font_key": g[0]["font_key"],
                "font_size": g[0]["font_size"],
                "original_text": combined_text,
                "blocks": g,
            }
        )
    return result


def extract_page_lines_for_canvas(
    page: PageObject,
) -> List[Tuple[float, float, float, float]]:
    """ดึงเส้นตาราง (m -> l -> S) จากหน้า PDF เพื่อวาดเป็นพื้นหลังอ้างอิงบนกระดานลากวาง"""
    contents = page.get_contents()
    if contents is None:
        return []
    raw_stream = contents.get_data().decode("latin-1", errors="ignore")
    matches = re.findall(
        r"([0-9.]+)\s+([0-9.]+)\s+m\s+([0-9.]+)\s+([0-9.]+)\s+l", raw_stream
    )
    return [(float(x1), float(y1), float(x2), float(y2)) for x1, y1, x2, y2 in matches]


def encode_text_to_bt_stream(
    text: str,
    x: float,
    y: float,
    font_size: float,
    orig_font_key: str,
    char_to_cid: Dict[str, int],
    ttf_info: Optional[Dict],
    force_custom_font: bool = False,
) -> Tuple[str, bool]:
    """
    แปลงข้อความให้เป็นคำสั่ง PDF BT ... ET
    - หากไม่ได้บังคับเปลี่ยนฟอนต์ และตัวอักษรทั้งหมดมีอยู่ในฟอนต์เดิมของเอกสาร จะใช้ฟอนต์เดิมของ PDF ทันที
    - หากมีตัวอักษรใหม่ หรือผู้ใช้เลือกเปลี่ยนฟอนต์ จะใช้ฟอนต์ TrueType ที่เลือก (ttf_info)
    """
    if not force_custom_font:
        expanded_for_orig = text
        if "\u0e33" in expanded_for_orig and "\u0e32" in char_to_cid:
            if "\u0e4d" in char_to_cid:
                expanded_for_orig = expanded_for_orig.replace("\u0e33", "\u0e4d\u0e32")
            elif "\u0e33" in char_to_cid:
                expanded_for_orig = expanded_for_orig.replace("\u0e33", "\u0e33\u0e32")

        can_use_original = all(ch in char_to_cid for ch in expanded_for_orig)
        if can_use_original and expanded_for_orig:
            hex_cids = "".join(f"{char_to_cid[ch]:04x}" for ch in expanded_for_orig)
            bt = f"BT\n1 0 0 1 {x:.4f} {y:.4f} Tm\n{orig_font_key} {font_size:g} Tf\n[<{hex_cids}> 0] TJ\nET"
            return bt, False

    if ttf_info:
        char_to_gid = ttf_info["char_to_gid"]
        res_name = ttf_info["pdf_res_name"]
        gids = []
        for ch in text:
            gid = char_to_gid.get(ord(ch))
            if gid is not None:
                gids.append(f"{gid:04x}")
            elif ord(" ") in char_to_gid:
                gids.append(f"{char_to_gid[ord(' ')]:04x}")
        hex_gids = "".join(gids)
        bt = f"BT\n1 0 0 1 {x:.4f} {y:.4f} Tm\n{res_name} {font_size:g} Tf\n[<{hex_gids}> 0] TJ\nET"
        return bt, True

    return f"BT\n1 0 0 1 {x:.4f} {y:.4f} Tm\n{orig_font_key} {font_size:g} Tf\n[] TJ\nET", False


def apply_text_modifications_to_page(
    writer: PdfWriter,
    page: PageObject,
    groups: List[Dict],
    new_texts: List[str],
    highlight_configs: Optional[List[Dict]] = None,
    extra_texts: Optional[List[Dict]] = None,
    selected_font_key: str = "auto",
    detected_fonts: Optional[List[str]] = None,
    available_fonts: Optional[Dict[str, Dict]] = None,
) -> None:
    """
    นำการแก้ไขข้อความ, การไฮไลต์ข้อความพร้อมข้อความต่อท้ายในบรรทัดเดียวกัน,
    และข้อความที่ลากวาง (แต่ละกล่องเลือกฟอนต์แยกได้) ไปอัปเดตลงในหน้า PDF
    """
    font_maps = repair_page_tounicode(page)
    contents = page.get_contents()
    if contents is None:
        return

    raw_stream = contents.get_data().decode("latin-1", errors="ignore")

    if available_fonts is None:
        available_fonts = load_builtin_fonts_catalog()
    if detected_fonts is None:
        detected_fonts = []

    resolved_main_font_key = resolve_best_font_key(
        selected_font_key, detected_fonts, available_fonts
    )
    main_ttf_info = available_fonts.get(resolved_main_font_key)
    force_custom_main = selected_font_key != "auto"

    if highlight_configs is None:
        highlight_configs = [{} for _ in groups]
    if extra_texts is None:
        extra_texts = []

    replacements: List[Tuple[int, int, str]] = []
    # เก็บรายการตัวอักษรที่ต้องฝังแยกตามชื่อฟอนต์ (font_id -> list of strings)
    used_chars_by_font: Dict[str, List[str]] = {}

    for grp, updated_text, hl_cfg in zip(groups, new_texts, highlight_configs):
        blocks = grp["blocks"]
        first_blk = blocks[0]
        _, char_to_cid, cid_widths = font_maps.get(first_blk["font_key"], ({}, {}, {}))

        is_highlighted = bool(hl_cfg.get("highlight", False))
        hl_subtext = str(hl_cfg.get("subtext", "")).strip()
        append_text = str(hl_cfg.get("append_text", "")).strip()
        hl_color: Tuple[float, float, float] = hl_cfg.get("hl_color", (1.0, 0.95, 0.35))
        append_color: Tuple[float, float, float] = hl_cfg.get(
            "append_color", (0.82, 0.08, 0.08)
        )
        highlight_append_too = bool(hl_cfg.get("highlight_append_too", False))

        text_changed = updated_text != grp["original_text"]

        if not text_changed and not is_highlighted and not append_text:
            continue

        font_size = first_blk["font_size"]
        base_x = first_blk["x"]
        base_y = first_blk["y"]

        if not text_changed:
            main_width = grp["width"]
            main_end_x = grp["end_x"]
        else:
            main_width = compute_text_width_pt(
                updated_text, font_size, char_to_cid, cid_widths, main_ttf_info
            )
            main_end_x = base_x + main_width

        # 1. วาดแถบสีไฮไลต์
        prefix_cmd = ""
        if is_highlighted and updated_text.strip():
            hr, hg, hb = hl_color
            hl_x = base_x
            hl_w = main_width

            if hl_subtext and hl_subtext in updated_text:
                pos = updated_text.find(hl_subtext)
                prefix_part = updated_text[:pos]
                hl_x = base_x + compute_text_width_pt(
                    prefix_part, font_size, char_to_cid, cid_widths, main_ttf_info
                )
                hl_w = compute_text_width_pt(
                    hl_subtext, font_size, char_to_cid, cid_widths, main_ttf_info
                )

            if (
                append_text
                and highlight_append_too
                and (not hl_subtext or hl_subtext == updated_text)
            ):
                append_w = compute_text_width_pt(
                    " " + append_text, font_size, char_to_cid, cid_widths, main_ttf_info
                )
                hl_w += append_w + 4.0

            hl_y = base_y - (0.24 * font_size)
            hl_h = 1.14 * font_size
            prefix_cmd = (
                f"q\n{hr:.3f} {hg:.3f} {hb:.3f} rg\n"
                f"{hl_x - 1.5:.2f} {hl_y:.2f} {hl_w + 3.0:.2f} {hl_h:.2f} re\nf\nQ\n"
            )

        # 2. วาดข้อความต่อท้ายในบรรทัดเดียวกัน
        suffix_cmd = ""
        if append_text:
            append_x = main_end_x + 5.0
            append_bt, used_custom_app = encode_text_to_bt_stream(
                text=append_text,
                x=append_x,
                y=base_y,
                font_size=font_size,
                orig_font_key=first_blk["font_key"],
                char_to_cid=char_to_cid,
                ttf_info=main_ttf_info,
                force_custom_font=force_custom_main,
            )
            if used_custom_app and main_ttf_info:
                used_chars_by_font.setdefault(resolved_main_font_key, []).append(
                    append_text
                )

            ar, ag, ab = append_color
            suffix_cmd = f"\nq\n{ar:.3f} {ag:.3f} {ab:.3f} rg\n{append_bt}\nQ"

        # 3. อัปเดตบล็อกข้อความหลัก
        if not text_changed:
            s0, e0 = first_blk["span"]
            orig_first_bt = raw_stream[s0:e0]
            s_last, e_last = blocks[-1]["span"]
            if len(blocks) == 1:
                replacements.append((s0, e0, prefix_cmd + orig_first_bt + suffix_cmd))
            else:
                if prefix_cmd:
                    replacements.append((s0, e0, prefix_cmd + orig_first_bt))
                if suffix_cmd:
                    orig_last_bt = raw_stream[s_last:e_last]
                    replacements.append((s_last, e_last, orig_last_bt + suffix_cmd))
        else:
            if updated_text.strip() == "":
                for idx_b, blk in enumerate(blocks):
                    s, e = blk["span"]
                    empty_bt = (
                        f"BT\n1 0 0 1 {blk['x']:.4f} {blk['y']:.4f} Tm\n"
                        f"{blk['font_key']} {blk['font_size']:g} Tf\n[] TJ\nET"
                    )
                    if idx_b == 0 and suffix_cmd:
                        empty_bt += suffix_cmd
                    replacements.append((s, e, empty_bt))
            else:
                new_bt, used_custom = encode_text_to_bt_stream(
                    text=updated_text,
                    x=base_x,
                    y=base_y,
                    font_size=font_size,
                    orig_font_key=first_blk["font_key"],
                    char_to_cid=char_to_cid,
                    ttf_info=main_ttf_info,
                    force_custom_font=force_custom_main,
                )
                if used_custom and main_ttf_info:
                    used_chars_by_font.setdefault(resolved_main_font_key, []).append(
                        updated_text
                    )

                s0, e0 = first_blk["span"]
                replacements.append((s0, e0, prefix_cmd + new_bt + suffix_cmd))

                for blk in blocks[1:]:
                    s, e = blk["span"]
                    empty_bt = (
                        f"BT\n1 0 0 1 {blk['x']:.4f} {blk['y']:.4f} Tm\n"
                        f"{blk['font_key']} {blk['font_size']:g} Tf\n[] TJ\nET"
                    )
                    replacements.append((s, e, empty_bt))

    modified_stream = raw_stream
    for start_idx, end_idx, rep_str in sorted(
        replacements, key=lambda x: x[0], reverse=True
    ):
        modified_stream = (
            modified_stream[:start_idx] + rep_str + modified_stream[end_idx:]
        )

    # 4. วาดกล่องข้อความที่ผู้ใช้ลากวาง (แต่ละกล่องสามารถเลือกฟอนต์ของตัวเองได้)
    page_height = float(page.mediabox.height)
    is_flipped_ctm = "1 0 0 -1 " in raw_stream
    _, first_char_to_cid, first_cid_widths = (
        next(iter(font_maps.values())) if font_maps else ({}, {}, {})
    )

    for item in extra_texts:
        txt = str(item.get("text", "")).strip()
        if not txt:
            continue
        left_pt = float(item.get("x", 50.0))
        top_pt = float(item.get("top_y", 100.0))
        sz = float(item.get("size", 14.0))
        color_hex = str(item.get("color", "#d11414"))
        bg_hex = str(item.get("bg_color", ""))
        box_font_req = str(item.get("font", selected_font_key))

        box_font_key = resolve_best_font_key(
            box_font_req, detected_fonts, available_fonts
        )
        box_ttf_info = available_fonts.get(box_font_key, main_ttf_info)
        force_box_custom = box_font_req != "auto"

        pdf_x = left_pt
        pdf_y = page_height - top_pt - (0.85 * sz)

        tr_r, tr_g, tr_b = hex_to_rgb_float(color_hex)

        bg_cmd = ""
        if bg_hex and bg_hex.startswith("#"):
            br, bg_g, bb = hex_to_rgb_float(bg_hex)
            box_w = compute_text_width_pt(
                txt,
                sz,
                {} if force_box_custom else first_char_to_cid,
                {} if force_box_custom else first_cid_widths,
                box_ttf_info,
            )
            hl_y = pdf_y - (0.24 * sz)
            hl_h = 1.14 * sz
            bg_cmd = (
                f"q\n{br:.3f} {bg_g:.3f} {bb:.3f} rg\n"
                f"{pdf_x - 2.0:.2f} {hl_y:.2f} {box_w + 4.0:.2f} {hl_h:.2f} re\nf\nQ\n"
            )

        bt_cmd, used_custom_box = encode_text_to_bt_stream(
            text=txt,
            x=pdf_x,
            y=pdf_y,
            font_size=sz,
            orig_font_key="/F1" if "/F1" in font_maps else "/FThai",
            char_to_cid=first_char_to_cid,
            ttf_info=box_ttf_info,
            force_custom_font=force_box_custom,
        )
        if used_custom_box and box_ttf_info:
            used_chars_by_font.setdefault(box_font_key, []).append(txt)

        if is_flipped_ctm:
            modified_stream += (
                f"\nq\n1 0 0 -1 0 {page_height:g} cm\n"
                f"{bg_cmd}"
                f"{tr_r:.3f} {tr_g:.3f} {tr_b:.3f} rg\n"
                f"{bt_cmd}\nQ\n"
            )
        else:
            modified_stream += (
                f"\nq\n{bg_cmd}"
                f"{tr_r:.3f} {tr_g:.3f} {tr_b:.3f} rg\n"
                f"{bt_cmd}\nQ\n"
            )

    # ฝังฟอนต์ที่ถูกใช้งานลงในหน้า PDF
    for f_key, char_list in used_chars_by_font.items():
        if f_key in available_fonts:
            embed_selected_font_on_page(
                writer, page, available_fonts[f_key], "".join(char_list)
            )

    new_stream_obj = DecodedStreamObject()
    new_stream_obj.set_data(modified_stream.encode("latin-1", errors="ignore"))
    page[NameObject("/Contents")] = writer._add_object(new_stream_obj)


# ---------------------------------------------------------------------------
# ส่วนสร้างกระดานลากวางข้อความบนหน้า PDF (Interactive Drag & Drop Canvas)
# ---------------------------------------------------------------------------

def render_drag_and_drop_canvas(
    page_width: float,
    page_height: float,
    page_number: int,
    groups: List[Dict],
    lines: List[Tuple[float, float, float, float]],
    extra_items: List[Dict],
    available_fonts: Dict[str, Dict],
    default_font_key: str,
) -> None:
    """
    แสดงกระดานหน้ากระดาษ PDF ที่ผู้ใช้สามารถเลือกฟอนต์ คลิกเมาส์ค้างที่กล่องข้อความ
    แล้วลากไปวางตรงไหนก็ได้ พร้อมซิงค์กลับมายัง Streamlit อัตโนมัติ
    """
    svg_elements = []
    for x1, y1, x2, y2 in lines:
        svg_elements.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#d5d5d5" stroke-width="1" />'
        )
    for g in groups:
        gx = g["x"]
        gy = page_height - g["y"]
        gsz = g["font_size"]
        gtxt = html.escape(g["original_text"])
        svg_elements.append(
            f'<text x="{gx:.1f}" y="{gy:.1f}" font-size="{gsz:.1f}px" '
            f'font-family="Leelawadee UI, Tahoma, sans-serif" fill="#333333">{gtxt}</text>'
        )
    svg_bg_str = "".join(svg_elements)
    items_json = json.dumps(extra_items, ensure_ascii=False)

    # สร้างตัวเลือกฟอนต์ใน Toolbar ของกระดานลากวาง
    font_options_html = ['<option value="auto">🔄 อัตโนมัติ (ตามเอกสาร)</option>']
    for f_key, f_info in available_fonts.items():
        sel = "selected" if f_key == default_font_key else ""
        label_clean = html.escape(f_info.get("label", f_key))
        font_options_html.append(
            f'<option value="{html.escape(f_key)}" {sel}>{label_clean}</option>'
        )
    font_select_html = "".join(font_options_html)

    canvas_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            padding: 10px;
            font-family: 'Sarabun', "Leelawadee UI", Tahoma, sans-serif;
            background: linear-gradient(145deg, #f8fafc 0%, #eff6ff 100%);
            user-select: none;
        }}
        .toolbar {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            background: rgba(255, 255, 255, 0.96);
            padding: 12px 16px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            margin-bottom: 12px;
            box-shadow: 0 4px 15px rgba(15, 23, 42, 0.06);
        }}
        .toolbar input[type="text"] {{
            padding: 8px 12px;
            border: 1.5px solid #cbd5e1;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            min-width: 190px;
            outline: none;
            transition: all 0.2s;
        }}
        .toolbar input[type="text"]:focus {{
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }}
        .toolbar select, .toolbar input[type="number"] {{
            padding: 7px 10px;
            border: 1.5px solid #cbd5e1;
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            background: #f8fafc;
            outline: none;
            transition: all 0.2s;
        }}
        .toolbar select:hover, .toolbar input[type="number"]:hover {{
            border-color: #94a3b8;
            background: #ffffff;
        }}
        .btn {{
            padding: 8px 15px;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .btn-add {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
        }}
        .btn-add:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
        }}
        .btn-save {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
        }}
        .btn-save:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
        }}
        .status-badge {{
            font-size: 12.5px;
            color: #334155;
            background: #f1f5f9;
            padding: 6px 12px;
            border-radius: 6px;
            border-left: 3px solid #3b82f6;
            width: 100%;
            margin-top: 2px;
        }}
        .stage-wrapper {{
            display: flex;
            justify-content: center;
            overflow: auto;
            padding: 16px;
            background: #1e293b;
            background-image: radial-gradient(#334155 1px, transparent 1px);
            background-size: 18px 18px;
            border-radius: 12px;
            border: 1px solid #334155;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.35);
        }}
        .pdf-stage {{
            position: relative;
            width: {page_width:.1f}px;
            height: {page_height:.1f}px;
            background: #ffffff;
            border-radius: 3px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
            overflow: hidden;
        }}
        .bg-svg {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
        }}
        .drag-item {{
            position: absolute;
            z-index: 10;
            cursor: grab;
            padding: 2px 6px;
            border: 1.5px dashed #2563eb;
            border-radius: 5px;
            white-space: nowrap;
            line-height: 1.15;
            box-shadow: 0 3px 8px rgba(37, 99, 235, 0.22);
            transition: box-shadow 0.15s;
        }}
        .drag-item:hover {{
            border-color: #1d4ed8;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.32);
        }}
        .drag-item:active {{
            cursor: grabbing;
            border: 2px solid #e11d48;
            box-shadow: 0 6px 16px rgba(225, 29, 72, 0.35);
        }}
        .drag-item .coord-tip {{
            position: absolute;
            top: -21px;
            left: 0;
            background: #0f172a;
            color: #f8fafc;
            font-size: 10px;
            font-weight: 500;
            padding: 2px 6px;
            border-radius: 4px;
            pointer-events: none;
            opacity: 0.92;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .drag-item .del-btn {{
            margin-left: 6px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 50%;
            width: 17px;
            height: 17px;
            font-size: 11px;
            line-height: 15px;
            text-align: center;
            cursor: pointer;
            padding: 0;
            transition: 0.15s;
        }}
        .drag-item .del-btn:hover {{
            background: #dc2626;
            transform: scale(1.1);
        }}
    </style>
    </head>
    <body>
        <div class="toolbar">
            <input type="text" id="newTextInput" placeholder="พิมพ์ข้อความใหม่ที่นี่..." value="ข้อความใหม่ (ลากวางได้)" />
            <label style="font-size:13px;">ฟอนต์:
                <select id="newFontInput" style="max-width:210px;">
                    {font_select_html}
                </select>
            </label>
            <label style="font-size:13px;">ขนาด:
                <input type="number" id="newSizeInput" value="14" min="8" max="42" style="width:48px;" />
            </label>
            <label style="font-size:13px;">สีอักษร:
                <select id="newColorInput">
                    <option value="#d11414">🔴 สีแดง</option>
                    <option value="#000000">⚫ สีดำ</option>
                    <option value="#0d47a1">🔵 สีน้ำเงิน</option>
                    <option value="#1b5e20">🟢 สีเขียวเข้ม</option>
                </select>
            </label>
            <label style="font-size:13px;">พื้นหลัง:
                <select id="newBgInput">
                    <option value="">ไม่ใส่สีพื้นหลัง</option>
                    <option value="#fff259" selected>🟨 ไฮไลต์เหลือง</option>
                    <option value="#a6f9a6">🟩 ไฮไลต์เขียว</option>
                    <option value="#a6edff">🟦 ไฮไลต์ฟ้า</option>
                    <option value="#ffbfdf">🟪 ไฮไลต์ชมพู</option>
                </select>
            </label>
            <button class="btn btn-add" onclick="addNewBox()">➕ เพิ่มข้อความลงกระดาน</button>
            <button class="btn btn-save" onclick="syncToStreamlit(true)">✅ อัปเดตลงไฟล์ PDF ทันที</button>
            <div class="status-badge" id="statusBadge">💡 คลิกค้างที่กล่องข้อความเพื่อลากไปวางตำแหน่งใดก็ได้ (ดับเบิลคลิกที่กล่องเพื่อแก้ไขข้อความ)</div>
        </div>

        <div class="stage-wrapper">
            <div class="pdf-stage" id="pdfStage">
                <svg class="bg-svg" viewBox="0 0 {page_width:.1f} {page_height:.1f}">
                    {svg_bg_str}
                </svg>
            </div>
        </div>

        <script>
            const PAGE_NO = {page_number};
            const PAGE_W = {page_width:.1f};
            const PAGE_H = {page_height:.1f};
            let items = {items_json};

            const stage = document.getElementById("pdfStage");
            const badge = document.getElementById("statusBadge");

            function renderBoxes() {{
                stage.querySelectorAll(".drag-item").forEach(el => el.remove());

                items.forEach((item, idx) => {{
                    if (item.page !== PAGE_NO) return;

                    const box = document.createElement("div");
                    box.className = "drag-item";
                    box.style.left = item.x + "px";
                    box.style.top = item.top_y + "px";
                    box.style.fontSize = item.size + "px";
                    box.style.color = item.color || "#d11414";
                    box.style.backgroundColor = item.bg_color || "transparent";

                    const tip = document.createElement("span");
                    tip.className = "coord-tip";
                    const fName = item.font || "auto";
                    tip.innerText = `[${{fName}}] X:${{Math.round(item.x)}}, Y:${{Math.round(item.top_y)}}`;
                    box.appendChild(tip);

                    const txtSpan = document.createElement("span");
                    txtSpan.innerText = item.text;
                    box.appendChild(txtSpan);

                    const delBtn = document.createElement("button");
                    delBtn.className = "del-btn";
                    delBtn.innerText = "×";
                    delBtn.title = "ลบข้อความนี้";
                    delBtn.onmousedown = (e) => {{ e.stopPropagation(); }};
                    delBtn.onclick = (e) => {{
                        e.stopPropagation();
                        items.splice(idx, 1);
                        renderBoxes();
                        syncToStreamlit(false);
                    }};
                    box.appendChild(delBtn);

                    box.ondblclick = (e) => {{
                        e.stopPropagation();
                        const updated = prompt("แก้ไขข้อความ:", item.text);
                        if (updated !== null && updated.trim() !== "") {{
                            item.text = updated;
                            renderBoxes();
                            syncToStreamlit(false);
                        }}
                    }};

                    box.onmousedown = (e) => {{
                        if (e.target === delBtn) return;
                        e.preventDefault();
                        const startMouseX = e.clientX;
                        const startMouseY = e.clientY;
                        const origX = item.x;
                        const origY = item.top_y;

                        function onMouseMove(ev) {{
                            const dx = ev.clientX - startMouseX;
                            const dy = ev.clientY - startMouseY;
                            let nx = Math.max(0, Math.min(PAGE_W - 20, origX + dx));
                            let ny = Math.max(0, Math.min(PAGE_H - 15, origY + dy));
                            item.x = Math.round(nx * 10) / 10;
                            item.top_y = Math.round(ny * 10) / 10;
                            box.style.left = item.x + "px";
                            box.style.top = item.top_y + "px";
                            tip.innerText = `[${{fName}}] X:${{Math.round(item.x)}}, Y:${{Math.round(item.top_y)}}`;
                            badge.innerText = `📍 กำลังลาก "${{item.text}}" ไปที่ (X: ${{Math.round(item.x)}}, Y: ${{Math.round(item.top_y)}})`;
                        }}

                        function onMouseUp() {{
                            document.removeEventListener("mousemove", onMouseMove);
                            document.removeEventListener("mouseup", onMouseUp);
                            badge.innerText = `✅ วาง "${{item.text}}" ที่ (X: ${{Math.round(item.x)}}, Y: ${{Math.round(item.top_y)}}) เรียบร้อยแล้ว`;
                            syncToStreamlit(false);
                        }}

                        document.addEventListener("mousemove", onMouseMove);
                        document.addEventListener("mouseup", onMouseUp);
                    }};

                    stage.appendChild(box);
                }});
            }}

            function addNewBox() {{
                const txt = document.getElementById("newTextInput").value.trim();
                if (!txt) return;
                const fKey = document.getElementById("newFontInput").value;
                const sz = parseFloat(document.getElementById("newSizeInput").value) || 14;
                const col = document.getElementById("newColorInput").value;
                const bg = document.getElementById("newBgInput").value;

                const offset = (items.length * 22) % 180;
                items.push({{
                    page: PAGE_NO,
                    text: txt,
                    font: fKey,
                    x: 120 + offset,
                    top_y: 160 + offset,
                    size: sz,
                    color: col,
                    bg_color: bg
                }});
                renderBoxes();
                syncToStreamlit(false);
            }}

            function syncToStreamlit(showNotice) {{
                try {{
                    const parentDoc = window.parent.document;
                    const bridgeInput = parentDoc.querySelector('input[aria-label="DRAG_BRIDGE_JSON"]');
                    if (bridgeInput) {{
                        const nativeSetter = Object.getOwnPropertyDescriptor(
                            window.parent.HTMLInputElement.prototype,
                            "value"
                        ).set;
                        nativeSetter.call(bridgeInput, JSON.stringify(items));
                        bridgeInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                        bridgeInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
                        bridgeInput.dispatchEvent(new KeyboardEvent("keydown", {{
                            key: "Enter",
                            code: "Enter",
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        }}));
                        bridgeInput.blur();
                        if (showNotice) {{
                            badge.innerText = "✅ อัปเดตตำแหน่งลงในไฟล์ PDF เรียบร้อยแล้ว! สามารถกดดาวน์โหลดด้านล่างได้เลย";
                        }}
                    }}
                }} catch (err) {{
                    console.error("Sync error:", err);
                }}
            }}

            renderBoxes();
        </script>
    </body>
    </html>
    """
    components.html(canvas_html, height=int(page_height) + 135, scrolling=True)


def render_pdf_preview(pdf_bytes: bytes, height: int = 720) -> None:
    """
    แสดงตัวอย่างไฟล์ PDF บนหน้าเว็บด้วย PDF.js (วาดลงบน HTML5 <canvas>)
    แก้ปัญหา Google Chrome และ Streamlit Cloud บล็อก <iframe src="data:application/pdf;base64,...">
    """
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    preview_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            padding: 14px;
            background: #0f172a;
            background-image: radial-gradient(#1e293b 1px, transparent 1px);
            background-size: 18px 18px;
            font-family: 'Sarabun', "Leelawadee UI", Tahoma, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 16px;
            border-radius: 14px;
        }}
        .top-bar {{
            width: 100%;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: space-between;
            align-items: center;
            background: rgba(30, 41, 59, 0.92);
            backdrop-filter: blur(8px);
            color: #f8fafc;
            padding: 10px 16px;
            border-radius: 10px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            font-size: 13.5px;
            font-weight: 500;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
        }}
        .badge-live {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .dot-live {{
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 8px #22c55e;
        }}
        .open-tab-btn {{
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border: none;
            padding: 7px 14px;
            border-radius: 7px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 600;
            font-size: 12.5px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
        }}
        .open-tab-btn:hover {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.45);
        }}
        #pdf-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
            width: 100%;
            padding-bottom: 12px;
        }}
        canvas {{
            background: white;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55);
            border-radius: 4px;
            max-width: 100%;
            height: auto !important;
        }}
    </style>
    </head>
    <body>
        <div class="top-bar">
            <span class="badge-live"><span class="dot-live"></span><span id="page-info">กำลังโหลดตัวอย่างเอกสาร PDF...</span></span>
            <button class="open-tab-btn" onclick="openInNewTab()">🔍 เปิดดู PDF ขนาดเต็มในแท็บใหม่</button>
        </div>
        <div id="pdf-container"></div>

        <script>
            const b64Data = "{b64_pdf}";
            const raw = atob(b64Data);
            const uint8Array = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) {{
                uint8Array[i] = raw.charCodeAt(i);
            }}

            function openInNewTab() {{
                const blob = new Blob([uint8Array], {{ type: "application/pdf" }});
                const url = URL.createObjectURL(blob);
                window.open(url, "_blank");
            }}

            const pdfjsLib = window["pdfjs-dist/build/pdf"];
            pdfjsLib.GlobalWorkerOptions.workerSrc =
                "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

            pdfjsLib.getDocument({{
                data: uint8Array,
                cMapUrl: "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/",
                cMapPacked: true,
                standardFontDataUrl: "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/standard_fonts/"
            }}).promise.then(function(pdfDoc) {{
                document.getElementById("page-info").innerText =
                    "แสดงผลจริง (Live Preview) • ทั้งหมด " + pdfDoc.numPages + " หน้า";
                const container = document.getElementById("pdf-container");

                for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {{
                    const canvas = document.createElement("canvas");
                    container.appendChild(canvas);
                    pdfDoc.getPage(pageNum).then(function(page) {{
                        const scale = 1.45;
                        const viewport = page.getViewport({{ scale: scale }});
                        const context = canvas.getContext("2d");
                        canvas.height = viewport.height;
                        canvas.width = viewport.width;
                        page.render({{
                            canvasContext: context,
                            viewport: viewport
                        }});
                    }});
                }}
            }}).catch(function(err) {{
                document.getElementById("page-info").innerText =
                    "ไม่สามารถเรนเดอร์ตัวอย่างได้: " + err.message;
            }});
        </script>
    </body>
    </html>
    """
    components.html(preview_html, height=height, scrolling=True)


def inject_custom_theme_css() -> None:
    """ตกแต่งหน้าเว็บ Streamlit ให้สวยงาม ทันสมัย ด้วยโทนสีและการ์ดระดับมืออาชีพ"""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Sarabun', 'Leelawadee UI', Tahoma, sans-serif;
        }

        /* พื้นหลังหลักของแอป */
        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        }

        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 97% !important;
        }

        /* แบนเนอร์ส่วนหัว (Hero Header) */
        .hero-banner {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
            color: #ffffff;
            padding: 24px 30px;
            border-radius: 18px;
            box-shadow: 0 10px 28px rgba(30, 58, 138, 0.22);
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .hero-title {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0 0 6px 0;
            letter-spacing: -0.01em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .hero-subtitle {
            font-size: 0.98rem;
            color: #dbeafe;
            margin: 0;
            font-weight: 400;
            line-height: 1.5;
        }
        .hero-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .hero-badge {
            background: rgba(255, 255, 255, 0.14);
            backdrop-filter: blur(6px);
            border: 1px solid rgba(255, 255, 255, 0.24);
            color: #f8fafc;
            padding: 6px 13px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            white-space: nowrap;
        }

        /* การ์ดแสดงข้อมูลสถิติ (Metric Cards) */
        div[data-testid="stMetric"] {
            background: #ffffff;
            padding: 14px 18px;
            border-radius: 14px;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #2563eb;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.09);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
            color: #64748b !important;
            font-weight: 600 !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
            color: #0f172a !important;
            font-weight: 700 !important;
        }

        /* กล่องอัปโหลดไฟล์ PDF */
        div[data-testid="stFileUploader"] {
            background: #ffffff;
            padding: 14px 18px;
            border-radius: 14px;
            border: 1.5px dashed #93c5fd;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.04);
        }

        /* แถบหัวข้อของฝั่งซ้ายและฝั่งขวา */
        .panel-header {
            background: #ffffff;
            padding: 12px 18px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            border-left: 5px solid #2563eb;
            margin-bottom: 12px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .panel-header-right {
            border-left-color: #10b981;
        }
        .panel-header-title {
            font-size: 1.12rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
        }
        .panel-header-tag {
            font-size: 0.78rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 999px;
            background: #eff6ff;
            color: #1d4ed8;
        }
        .panel-header-tag-right {
            background: #ecfdf5;
            color: #047857;
        }

        /* ปรับแต่งปุ่ม Tabs ให้ดูเหมือน Segmented Pill Bar */
        div[data-baseweb="tab-list"] {
            background: #e2e8f0;
            padding: 5px;
            border-radius: 12px;
            gap: 6px;
        }
        button[data-baseweb="tab"] {
            border-radius: 9px !important;
            padding: 8px 14px !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            color: #475569 !important;
            border: none !important;
            background: transparent !important;
            transition: all 0.2s ease !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: #ffffff !important;
            color: #1d4ed8 !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.1) !important;
        }
        div[data-baseweb="tab-highlight"] {
            display: none !important;
        }

        /* ปุ่มดาวน์โหลดหลัก */
        div[data-testid="stDownloadButton"] button {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.55rem 1.2rem !important;
            font-weight: 700 !important;
            font-size: 0.96rem !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28) !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stDownloadButton"] button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.38) !important;
            background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        }

        /* Expander สวยงาม */
        details[data-testid="stExpander"] {
            background: #ffffff;
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
            margin-bottom: 12px;
        }

        /* การ์ดต้อนรับตอนยังไม่อัปโหลดไฟล์ */
        .empty-state-card {
            background: #ffffff;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            padding: 32px 28px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
            margin-top: 12px;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 14px;
            margin-top: 22px;
            text-align: left;
        }
        .feature-item {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
        }
        .feature-item h4 {
            margin: 0 0 6px 0;
            color: #1e3a8a;
            font-size: 1rem;
        }
        .feature-item p {
            margin: 0;
            color: #475569;
            font-size: 0.88rem;
            line-height: 1.45;
        }

        /* ซ่อนช่อง Bridge Input */
        div[data-testid="stTextInput"]:has(input[aria-label="DRAG_BRIDGE_JSON"]) {
            position: fixed;
            left: -9999px;
            width: 1px;
            height: 1px;
            overflow: hidden;
            opacity: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_standalone_pdf_merger() -> None:
    """โหมดรวมไฟล์ PDF หลายไฟล์เข้าด้วยกันโดยเฉพาะ (Multi-PDF Merger Studio)"""
    st.markdown(
        """
        <div class="panel-header" style="border-left-color: #8b5cf6;">
            <span class="panel-header-title">📑 โหมดรวมไฟล์ PDF หลายไฟล์เข้าด้วยกัน (Multi-PDF Merger)</span>
            <span class="panel-header-tag" style="background:#f3e8ff; color:#6d28d9;">รองรับหลายไฟล์ • จัดลำดับ & เลือกหน้าได้</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    merge_files = st.file_uploader(
        "📂 เลือกไฟล์ PDF ทั้งหมดที่ต้องการนำมารวมกัน (กด Ctrl หรือ Shift ค้างไว้เพื่อเลือกพร้อมกันหลายไฟล์):",
        type=["pdf"],
        accept_multiple_files=True,
        key="standalone_multi_merger",
    )

    if not merge_files:
        st.markdown(
            """
            <div class="empty-state-card">
                <h3 style="margin:0 0 8px 0; color:#0f172a;">📑 อัปโหลดไฟล์ PDF ตั้งแต่ 2 ไฟล์ขึ้นไปเพื่อรวมเป็นไฟล์เดียว</h3>
                <p style="margin:0; color:#64748b;">คุณสามารถกำหนดลำดับก่อน-หลัง เลือกเฉพาะบางหน้าของแต่ละไฟล์ และดูตัวอย่าง PDF ที่รวมเสร็จแล้วด้านขวาได้ทันที</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    m_left, m_right = st.columns([1.05, 1.0], gap="medium")

    file_configs: List[Dict] = []

    with m_left:
        st.markdown(
            """
            <div class="panel-header">
                <span class="panel-header-title">🔢 จัดลำดับไฟล์และเลือกหน้าที่ต้องการรวม (ฝั่งซ้าย)</span>
                <span class="panel-header-tag">ตั้งค่าการรวมไฟล์</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("💡 ปรับตัวเลขในช่อง **ลำดับที่** เพื่อเรียงไฟล์ก่อน-หลัง และเลือกช่วงหน้าของแต่ละไฟล์ได้ตามต้องการ")

        for idx, mf in enumerate(merge_files, start=1):
            raw_bytes = mf.getvalue()
            try:
                r = PdfReader(io.BytesIO(raw_bytes))
                num_p = len(r.pages)
            except Exception as exc:
                st.error(f"ไฟล์ {mf.name} ไม่สามารถอ่านได้: {exc}")
                continue

            with st.container(border=True):
                c_ord, c_info, c_from, c_to = st.columns([1.1, 3.2, 1.2, 1.2])
                order_val = c_ord.number_input(
                    "ลำดับที่",
                    min_value=1,
                    max_value=len(merge_files),
                    value=idx,
                    step=1,
                    key=f"m_order_{idx}_{mf.name}",
                )
                c_info.markdown(f"**📄 {mf.name}**\n\nจำนวนทั้งหมด `{num_p}` หน้า")
                start_p = c_from.number_input(
                    "เริ่มหน้า",
                    min_value=1,
                    max_value=num_p,
                    value=1,
                    step=1,
                    key=f"m_start_{idx}_{mf.name}",
                )
                end_p = c_to.number_input(
                    "ถึงหน้า",
                    min_value=int(start_p),
                    max_value=num_p,
                    value=num_p,
                    step=1,
                    key=f"m_end_{idx}_{mf.name}",
                )

                file_configs.append(
                    {
                        "order": int(order_val),
                        "original_index": idx,
                        "name": mf.name,
                        "bytes": raw_bytes,
                        "start_page": int(start_p),
                        "end_page": int(end_p),
                    }
                )

    file_configs.sort(key=lambda x: (x["order"], x["original_index"]))

    merged_writer = PdfWriter()
    for cfg in file_configs:
        try:
            r = PdfReader(io.BytesIO(cfg["bytes"]))
            for p_idx in range(cfg["start_page"] - 1, cfg["end_page"]):
                if 0 <= p_idx < len(r.pages):
                    merged_writer.add_page(r.pages[p_idx])
        except Exception as exc:
            st.warning(f"ข้ามไฟล์ {cfg['name']}: {exc}")

    out_buf = io.BytesIO()
    merged_writer.write(out_buf)
    out_buf.seek(0)
    merged_bytes = out_buf.getvalue()

    with m_right:
        st.markdown(
            """
            <div class="panel-header panel-header-right">
                <span class="panel-header-title">👁️ ตัวอย่างไฟล์ PDF ที่รวมแล้ว & ดาวน์โหลด (ฝั่งขวา)</span>
                <span class="panel-header-tag panel-header-tag-right">รวมทั้งหมด """
            + f"{len(merged_writer.pages)} หน้า"
            + """</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        dl_c1, dl_c2 = st.columns([1.3, 1.2])
        merged_filename = dl_c1.text_input(
            "ชื่อไฟล์ที่รวมเสร็จแล้ว:",
            value="merged_document.pdf",
            label_visibility="collapsed",
            key="standalone_merged_filename",
        )
        if not merged_filename.lower().endswith(".pdf"):
            merged_filename += ".pdf"

        with dl_c2:
            st.download_button(
                label=f"⬇️ ดาวน์โหลดไฟล์ที่รวมแล้ว ({len(merged_writer.pages)} หน้า)",
                data=merged_bytes,
                file_name=merged_filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key="standalone_merged_dl_btn",
            )

        render_pdf_preview(merged_bytes, height=860)


def main() -> None:
    st.set_page_config(
        page_title="PDF Studio Pro - แก้ไข ลากวาง ไฮไลต์ & รวมไฟล์ PDF",
        page_icon="🖍️",
        layout="wide",
    )

    inject_custom_theme_css()

    st.markdown(
        """
        <div class="hero-banner">
            <div>
                <div class="hero-title">🖍️ PDF Studio Pro — ระบบจัดการ แก้ไข และรวมไฟล์เอกสาร PDF อัจฉริยะ</div>
                <p class="hero-subtitle">
                    ตรวจจับฟอนต์ไทย-อังกฤษอัตโนมัติ • ลากวางข้อความอิสระ • ไฮไลต์พร้อมพิมพ์ต่อท้าย • รวมไฟล์ PDF หลายไฟล์เข้าด้วยกัน • ดูผลลัพธ์จริงแบบซ้าย-ขวา
                </p>
            </div>
            <div class="hero-badges">
                <span class="hero-badge">🔤 รองรับหลายฟอนต์ (.TTF)</span>
                <span class="hero-badge">🖱️ ลากวางอิสระ</span>
                <span class="hero-badge">📑 รวมไฟล์ PDF</span>
                <span class="hero-badge">👁️ Live Preview คู่ขนาน</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "custom_uploaded_fonts" not in st.session_state:
        st.session_state["custom_uploaded_fonts"] = {}
    if "extra_texts" not in st.session_state:
        st.session_state["extra_texts"] = []

    app_mode = st.radio(
        "เลือกโหมดการทำงาน:",
        options=[
            "🛠️ แก้ไขเอกสาร PDF (ลากวางข้อความ / ไฮไลต์ / แก้ไขคำ / แทรกและรวมไฟล์)",
            "📑 รวมไฟล์ PDF หลายไฟล์เข้าด้วยกัน (Multi-PDF Merger)",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    if app_mode.startswith("📑"):
        render_standalone_pdf_merger()
        return

    uploaded_file = st.file_uploader(
        "📂 อัปโหลดไฟล์เอกสาร PDF ที่ต้องการแก้ไข (ลากไฟล์มาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์)",
        type=["pdf"],
    )

    if uploaded_file is None:
        st.markdown(
            """
            <div class="empty-state-card">
                <h3 style="margin:0 0 8px 0; color:#0f172a;">👆 เริ่มต้นด้วยการอัปโหลดไฟล์ PDF ด้านบน</h3>
                <p style="margin:0; color:#64748b;">รองรับเอกสารภาษาไทยและภาษาอังกฤษ เช่น ใบเสนอราคา ใบแจ้งหนี้ สัญญา และเอกสารราชการ</p>
                <div class="feature-grid">
                    <div class="feature-item">
                        <h4>🖱️ 1. ลากวางข้อความอิสระ</h4>
                        <p>เพิ่มกล่องข้อความใหม่ เลือกฟอนต์ ขนาด สี และใช้เมาส์ลากไปวางตรงไหนของหน้ากระดาษก็ได้</p>
                    </div>
                    <div class="feature-item">
                        <h4>🖍️ 2. ไฮไลต์ & พิมพ์ต่อท้าย</h4>
                        <p>เน้นข้อความสำคัญด้วยสีไฮไลต์ พร้อมพิมพ์หมายเหตุต่อท้ายในบรรทัดเดียวกันได้ทันที</p>
                    </div>
                    <div class="feature-item">
                        <h4>✏️ 3. แก้ไขข้อความเดิม</h4>
                        <p>แก้คำผิด ตัวเลข วันที่ หรือค้นหาและแทนที่คำในเอกสารโดยรักษาตำแหน่งและฟอนต์เดิม</p>
                    </div>
                    <div class="feature-item">
                        <h4>🔤 4. รองรับฟอนต์หลากหลาย</h4>
                        <p>มาพร้อมฟอนต์ไทยมาตรฐาน (CSChatThai, TH Sarabun, Leelawadee, Tahoma) และอัปโหลด .ttf เพิ่มได้</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    raw_pdf_bytes = uploaded_file.getvalue()

    try:
        reader = PdfReader(io.BytesIO(raw_pdf_bytes))
        total_pages = len(reader.pages)
    except Exception as exc:
        st.error(f"ไม่สามารถอ่านไฟล์ PDF นี้ได้: {exc}")
        return

    detected_fonts = detect_pdf_fonts(reader)
    available_fonts = get_all_available_fonts()
    auto_matched_key = resolve_best_font_key("auto", detected_fonts, available_fonts)

    # แถบแสดงข้อมูลไฟล์และฟอนต์ที่ตรวจพบใน PDF
    col_m1, col_m2, col_m3, col_m4 = st.columns([2.2, 1.2, 2.5, 1.2])
    col_m1.metric("ชื่อไฟล์ต้นฉบับ", uploaded_file.name)
    col_m2.metric("จำนวนหน้าต้นฉบับ", f"{total_pages} หน้า")
    col_m3.metric(
        "🔤 ฟอนต์ในเอกสาร PDF นี้",
        ", ".join(detected_fonts) if detected_fonts else "ไม่ระบุ (ใช้ฟอนต์มาตรฐาน)",
    )

    # แถบตั้งค่าและเลือกฟอนต์ (Multi-Font Selector & Custom TTF Uploader)
    with st.expander("🔤 ตั้งค่าฟอนต์สำหรับแก้ไขและเพิ่มข้อความ (รองรับหลายฟอนต์ + อัปโหลดฟอนต์ .ttf เพิ่มได้)", expanded=True):
        f_col1, f_col2 = st.columns([2.5, 2])
        font_choice_keys = ["auto"] + list(available_fonts.keys())

        def format_font_option(k: str) -> str:
            if k == "auto":
                matched_label = available_fonts.get(auto_matched_key, {}).get("label", auto_matched_key)
                return f"🔄 อัตโนมัติ (ใช้ฟอนต์เดิมใน PDF + จับคู่ '{matched_label}')"
            return available_fonts[k].get("label", k)

        selected_font_key = f_col1.selectbox(
            "เลือกฟอนต์หลักสำหรับแก้ไขข้อความและพิมพ์ข้อความต่อท้าย:",
            options=font_choice_keys,
            format_func=format_font_option,
            index=0,
        )

        uploaded_ttf = f_col2.file_uploader(
            "➕ อัปโหลดไฟล์ฟอนต์ (.ttf) เพิ่มเติม (เช่น CSChatThai.ttf, Prompt.ttf):",
            type=["ttf"],
            key="custom_ttf_uploader",
        )
        if uploaded_ttf is not None:
            ttf_stem = os.path.splitext(uploaded_ttf.name)[0]
            if ttf_stem not in st.session_state["custom_uploaded_fonts"]:
                parsed_custom = parse_ttf_bytes(uploaded_ttf.getvalue(), ttf_stem)
                if parsed_custom:
                    parsed_custom["label"] = f"⭐ {ttf_stem} (ฟอนต์ที่อัปโหลด)"
                    st.session_state["custom_uploaded_fonts"][ttf_stem] = parsed_custom
                    st.success(f"เพิ่มฟอนต์ '{ttf_stem}' เข้าสู่ระบบเรียบร้อยแล้ว!")
                    st.rerun()
                else:
                    st.error("ไฟล์ .ttf นี้ไม่รองรับตาราง Unicode มาตรฐาน")

    bridge_val = st.text_input(
        "DRAG_BRIDGE_JSON",
        value=json.dumps(st.session_state["extra_texts"], ensure_ascii=False),
        key="drag_bridge_input",
    )
    try:
        parsed_bridge = json.loads(bridge_val)
        if isinstance(parsed_bridge, list):
            st.session_state["extra_texts"] = parsed_bridge
    except Exception:
        pass

    # แบ่งหน้าจอเป็น 2 ฝั่ง: ด้านซ้าย (เครื่องมือแก้ไข/กระดานลากวาง) และ ด้านขวา (ตัวอย่าง PDF จริง Live Preview + ดาวน์โหลด)
    left_col, right_col = st.columns([1.05, 1.0], gap="medium")

    with left_col:
        st.markdown(
            """
            <div class="panel-header">
                <span class="panel-header-title">🛠️ พื้นที่แก้ไขเอกสาร PDF (Editor Studio)</span>
                <span class="panel-header-tag">ฝั่งซ้าย • แก้ไขข้อมูล</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        tab_drag, tab_highlight, tab_edit_text, tab_manage_pages = st.tabs(
            [
                "🖱️ 1. ลากวางข้อความ",
                "🖍️ 2. ไฮไลต์ & ต่อท้าย",
                "✏️ 3. แก้ไขข้อความเดิม",
                "📑 4. รวมไฟล์ & จัดการหน้า",
            ]
        )

        page_groups_map: Dict[int, List[Dict]] = {}
        edited_texts_map: Dict[int, List[str]] = {}
        highlight_configs_map: Dict[int, List[Dict]] = {}

        for pno in range(1, total_pages + 1):
            page_groups_map[pno] = parse_page_text_groups(reader.pages[pno - 1])

        # -----------------------------------------------------------------------
        # แท็บที่ 1: เพิ่มข้อความลงในไฟล์แบบลากวางตรงไหนก็ได้ (Drag & Drop)
        # -----------------------------------------------------------------------
        with tab_drag:
            st.markdown(
                "1. พิมพ์ข้อความ **เลือกฟอนต์** ขนาด สีตัวอักษร และสีไฮไลต์พื้นหลัง แล้วกดปุ่ม **`➕ เพิ่มข้อความลงกระดาน`**\n"
                "2. **คลิกเมาส์ค้างที่กล่องข้อความบนหน้ากระดาษ** แล้วลากไปวางตำแหน่งใดก็ได้ตามต้องการ (ดูผลลัพธ์จริงเทียบกับ **ฝั่งขวา** ได้ทันที)"
            )

            selected_drag_page = (
                st.selectbox(
                    "เลือกหน้าที่ต้องการวางข้อความ:",
                    options=list(range(1, total_pages + 1)),
                    format_func=lambda x: f"หน้าที่ {x}",
                )
                if total_pages > 1
                else 1
            )

            target_page_obj = reader.pages[selected_drag_page - 1]
            pw = float(target_page_obj.mediabox.width)
            ph = float(target_page_obj.mediabox.height)
            page_lines = extract_page_lines_for_canvas(target_page_obj)

            render_drag_and_drop_canvas(
                page_width=pw,
                page_height=ph,
                page_number=selected_drag_page,
                groups=page_groups_map[selected_drag_page],
                lines=page_lines,
                extra_items=st.session_state["extra_texts"],
                available_fonts=available_fonts,
                default_font_key=selected_font_key,
            )

            if st.session_state["extra_texts"]:
                if st.button("🗑️ ล้างกล่องข้อความที่ลากวางทั้งหมด"):
                    st.session_state["extra_texts"] = []
                    st.rerun()

        # -----------------------------------------------------------------------
        # แท็บที่ 2: ไฮไลต์ข้อความ และเพิ่มข้อความต่อท้ายในบรรทัดนั้น
        # -----------------------------------------------------------------------
        with tab_highlight:
            opt_col1, opt_col2, opt_col3 = st.columns([2, 2, 2])
            selected_hl_color_name = opt_col1.selectbox(
                "🎨 เลือกสีไฮไลต์:",
                options=list(HIGHLIGHT_COLORS.keys()),
                index=0,
            )
            selected_append_color_name = opt_col2.selectbox(
                "🖋️ สีข้อความต่อท้าย:",
                options=list(APPEND_TEXT_COLORS.keys()),
                index=1,
            )
            highlight_append_too = opt_col3.checkbox(
                "คลุมสีไฮไลต์ข้อความต่อท้ายด้วย",
                value=False,
            )

            default_hl_rgb = HIGHLIGHT_COLORS[selected_hl_color_name]
            default_append_rgb = APPEND_TEXT_COLORS[selected_append_color_name]

            with st.expander("⚡ ไฮไลต์และเพิ่มข้อความต่อท้ายแบบระบุคำค้นหา (Quick Highlight & Append)", expanded=True):
                q_col1, q_col2, q_col3 = st.columns([2, 2, 1.2])
                q_keyword = q_col1.text_input(
                    "คำที่ต้องการไฮไลต์:",
                    key="q_kw_input",
                )
                q_append = q_col2.text_input(
                    "ข้อความต่อท้ายในบรรทัดนั้น:",
                    key="q_app_input",
                )
                q_only_sub = q_col3.checkbox(
                    "ไฮไลต์เฉพาะคำค้น",
                    value=True,
                )

            filter_kw = st.text_input(
                "🔍 กรองดูเฉพาะบรรทัดที่ต้องการ (เว้นว่างเพื่อแสดงทุกบรรทัด):",
                value="",
            )

            for pno in range(1, total_pages + 1):
                groups = page_groups_map[pno]
                st.markdown(f"#### 📄 หน้าที่ {pno}")
                if not groups:
                    st.info("หน้านี้ไม่มีบล็อกข้อความ")
                    highlight_configs_map[pno] = []
                    continue

                hl_cfgs_for_page: List[Dict] = []

                h_c1, h_c2, h_c3 = st.columns([1.2, 4, 3.5])
                h_c1.markdown("**ไฮไลต์**")
                h_c2.markdown("**ข้อความในบรรทัด**")
                h_c3.markdown("**➕ ข้อความต่อท้าย**")

                with st.container(height=600, border=True):
                    for idx, g in enumerate(groups, start=1):
                        orig_txt = g["original_text"]

                        matched_sub = match_keyword_in_text(q_keyword, orig_txt)
                        matched_quick = matched_sub is not None
                        default_checked = matched_quick
                        default_app_txt = q_append if matched_quick else ""

                        if filter_kw.strip() and match_keyword_in_text(filter_kw, orig_txt) is None:
                            hl_cfgs_for_page.append(
                                {
                                    "highlight": default_checked,
                                    "subtext": matched_sub if (matched_quick and q_only_sub) else "",
                                    "append_text": default_app_txt,
                                    "hl_color": default_hl_rgb,
                                    "append_color": default_append_rgb,
                                    "highlight_append_too": highlight_append_too,
                                }
                            )
                            continue

                        r_c1, r_c2, r_c3 = st.columns([1.2, 4, 3.5])
                        is_hl = r_c1.checkbox(
                            f"🖍️ #{idx}",
                            value=default_checked,
                            key=f"hl_chk_{pno}_{idx}_{uploaded_file.name}_{q_keyword}",
                        )
                        r_c2.markdown(f"`{orig_txt}`")
                        app_txt = r_c3.text_input(
                            label=f"ต่อท้ายบรรทัดที่ {idx}",
                            value=default_app_txt,
                            placeholder="พิมพ์ข้อความต่อท้าย...",
                            key=f"hl_app_{pno}_{idx}_{uploaded_file.name}_{q_keyword}_{q_append}",
                            label_visibility="collapsed",
                        )

                        effective_hl = is_hl or bool(app_txt.strip())

                        hl_cfgs_for_page.append(
                            {
                                "highlight": effective_hl,
                                "subtext": matched_sub if (matched_quick and q_only_sub) else "",
                                "append_text": app_txt,
                                "hl_color": default_hl_rgb,
                                "append_color": default_append_rgb,
                                "highlight_append_too": highlight_append_too,
                            }
                        )

                highlight_configs_map[pno] = hl_cfgs_for_page

        # -----------------------------------------------------------------------
        # แท็บที่ 3: แก้ไขข้อความเดิม / ค้นหาและแทนที่คำ
        # -----------------------------------------------------------------------
        with tab_edit_text:
            with st.expander("🔎 ค้นหาและแทนที่ข้อความด่วน (Find & Replace)", expanded=True):
                fr_col1, fr_col2 = st.columns(2)
                find_str = fr_col1.text_input("คำที่ต้องการค้นหา (เช่น 12/11/2026 หรือ 2,500.00):")
                replace_str = fr_col2.text_input("แทนที่ด้วยคำใหม่:")

            for pno in range(1, total_pages + 1):
                groups = page_groups_map[pno]
                st.markdown(f"#### 📄 หน้าที่ {pno}")
                if not groups:
                    edited_texts_map[pno] = []
                    continue

                edited_list: List[str] = []
                with st.container(height=620, border=True):
                    for idx, g in enumerate(groups, start=1):
                        orig_txt = g["original_text"]
                        default_txt = orig_txt
                        if find_str and find_str in default_txt:
                            default_txt = default_txt.replace(find_str, replace_str)

                        c_idx, c_edit = st.columns([1.2, 5])
                        c_idx.caption(f"#{idx} (Y={g['y']:.0f})")
                        new_val = c_edit.text_input(
                            label=f"ข้อความจุดที่ {idx}",
                            value=default_txt,
                            key=f"txt_{pno}_{idx}_{uploaded_file.name}_{find_str}_{replace_str}",
                            label_visibility="collapsed",
                        )
                        edited_list.append(new_val)

                edited_texts_map[pno] = edited_list

        # -----------------------------------------------------------------------
        # แท็บที่ 4: จัดการหน้ากระดาษ & รวมไฟล์ PDF
        # -----------------------------------------------------------------------
        with tab_manage_pages:
            all_page_numbers = list(range(1, total_pages + 1))

            st.markdown("##### 📑 1) รวมไฟล์ PDF อื่นเข้ากับเอกสารนี้ (Merge Multiple PDFs)")
            merged_pdf_files = st.file_uploader(
                "อัปโหลดไฟล์ PDF ที่ต้องการนำมารวม (เลือกพร้อมกันได้หลายไฟล์):",
                type=["pdf"],
                accept_multiple_files=True,
                key="merge_uploader",
            )

            merge_configs_by_pos: Dict[int, List[Dict]] = {}
            if merged_pdf_files:
                st.caption("ตั้งค่าตำแหน่งแทรกและช่วงหน้าของแต่ละไฟล์ที่ต้องการนำมารวม:")
                pos_options = [0] + all_page_numbers
                for m_idx, m_file in enumerate(merged_pdf_files, start=1):
                    m_bytes = m_file.getvalue()
                    try:
                        m_reader_info = PdfReader(io.BytesIO(m_bytes))
                        m_total = len(m_reader_info.pages)
                    except Exception as exc:
                        st.error(f"ไม่สามารถอ่านไฟล์ {m_file.name}: {exc}")
                        continue

                    with st.container(border=True):
                        st.markdown(f"**{m_idx}. 📄 {m_file.name}** (`{m_total}` หน้า)")
                        mc1, mc2, mc3 = st.columns([2.2, 1.1, 1.1])
                        insert_pos = mc1.selectbox(
                            "ตำแหน่งที่ต้องการวาง:",
                            options=pos_options,
                            index=len(pos_options) - 1,
                            format_func=lambda x: (
                                "⬆️ ไว้หน้าแรกสุด (ก่อนหน้า 1)"
                                if x == 0
                                else (
                                    f"⬇️ ต่อท้ายเอกสาร (หลังหน้า {total_pages})"
                                    if x == total_pages
                                    else f"📌 แทรกต่อจากหน้าที่ {x}"
                                )
                            ),
                            key=f"m_pos_{m_idx}_{m_file.name}",
                        )
                        m_from = mc2.number_input(
                            "เริ่มหน้า:",
                            min_value=1,
                            max_value=m_total,
                            value=1,
                            step=1,
                            key=f"m_from_{m_idx}_{m_file.name}",
                        )
                        m_to = mc3.number_input(
                            "ถึงหน้า:",
                            min_value=int(m_from),
                            max_value=m_total,
                            value=m_total,
                            step=1,
                            key=f"m_to_{m_idx}_{m_file.name}",
                        )
                        merge_configs_by_pos.setdefault(int(insert_pos), []).append(
                            {
                                "name": m_file.name,
                                "bytes": m_bytes,
                                "from_page": int(m_from),
                                "to_page": int(m_to),
                            }
                        )

            st.divider()

            st.markdown("##### ➕ 2) เพิ่มหน้าเปล่า (Blank Page)")
            blank_options = [0] + all_page_numbers
            blank_pages_after = st.multiselect(
                "เลือกตำแหน่งที่ต้องการแทรกหน้าเปล่า:",
                options=blank_options,
                format_func=lambda x: "ก่อนหน้าแรกสุด (หน้า 1)" if x == 0 else f"ต่อท้ายหน้าที่ {x}",
            )

            st.divider()

            st.markdown("##### 🗑️ 3) ลบหน้าที่ไม่ต้องการออก")
            pages_to_delete = st.multiselect(
                "เลือกเลขหน้าที่ต้องการลบออก:",
                options=all_page_numbers,
                format_func=lambda x: f"หน้าที่ {x}",
            )

    # -----------------------------------------------------------------------
    # ประมวลผลสร้างไฟล์ PDF ใหม่
    # -----------------------------------------------------------------------
    writer = PdfWriter()
    fresh_reader = PdfReader(io.BytesIO(raw_pdf_bytes))

    default_width = 595.0
    default_height = 842.0
    if len(fresh_reader.pages) > 0:
        first_box = fresh_reader.pages[0].mediabox
        default_width = float(first_box.width)
        default_height = float(first_box.height)

    delete_set = set(pages_to_delete)
    blank_set = set(blank_pages_after)

    def _append_merged_at(position_idx: int) -> None:
        for cfg in merge_configs_by_pos.get(position_idx, []):
            try:
                m_reader = PdfReader(io.BytesIO(cfg["bytes"]))
                for p_i in range(cfg["from_page"] - 1, cfg["to_page"]):
                    if 0 <= p_i < len(m_reader.pages):
                        writer.add_page(m_reader.pages[p_i])
            except Exception as exc:
                st.warning(f"ไม่สามารถรวมไฟล์ {cfg['name']}: {exc}")

    if 0 in blank_set:
        writer.add_page(
            PageObject.create_blank_page(width=default_width, height=default_height)
        )
    _append_merged_at(0)

    for idx in range(1, total_pages + 1):
        if idx not in delete_set:
            page_copy = fresh_reader.pages[idx - 1]
            extra_for_page = [
                item
                for item in st.session_state["extra_texts"]
                if int(item.get("page", 1)) == idx
            ]
            apply_text_modifications_to_page(
                writer=writer,
                page=page_copy,
                groups=page_groups_map.get(idx, []),
                new_texts=edited_texts_map.get(idx, []),
                highlight_configs=highlight_configs_map.get(idx, []),
                extra_texts=extra_for_page,
                selected_font_key=selected_font_key,
                detected_fonts=detected_fonts,
                available_fonts=available_fonts,
            )
            writer.add_page(page_copy)

        if idx in blank_set:
            writer.add_page(
                PageObject.create_blank_page(width=default_width, height=default_height)
            )
        _append_merged_at(idx)

    if len(writer.pages) == 0:
        st.warning("⚠️ คุณเลือกลบทุกหน้าในเอกสาร ระบบจึงสร้างหน้าเปล่า 1 หน้าไว้ให้แทน")
        writer.add_page(
            PageObject.create_blank_page(width=default_width, height=default_height)
        )

    col_m4.metric("จำนวนหน้าหลังแก้ไข", f"{len(writer.pages)} หน้า")

    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    modified_pdf_bytes = output_buffer.getvalue()

    with right_col:
        st.markdown(
            """
            <div class="panel-header panel-header-right">
                <span class="panel-header-title">👁️ ตัวอย่างเอกสาร PDF จริง & ดาวน์โหลด</span>
                <span class="panel-header-tag panel-header-tag-right">ฝั่งขวา • อัปเดตอัตโนมัติ</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        dl_col1, dl_col2 = st.columns([1.3, 1.2])
        original_stem = uploaded_file.name.rsplit(".", 1)[0]
        output_filename = dl_col1.text_input(
            "ชื่อไฟล์สำหรับดาวน์โหลด:",
            value=f"{original_stem}_edited.pdf",
            label_visibility="collapsed",
        )
        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"

        with dl_col2:
            st.download_button(
                label="⬇️ ดาวน์โหลดไฟล์ PDF ที่แก้ไขแล้ว",
                data=modified_pdf_bytes,
                file_name=output_filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        render_pdf_preview(modified_pdf_bytes, height=int(default_height) + 150)


if __name__ == "__main__":
    main()
