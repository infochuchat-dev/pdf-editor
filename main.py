"""
โปรแกรมจัดการไฟล์ PDF ด้วยไลบรารี pypdf (Pure Python - ไม่ติดปัญหา DLL Blocked บน Windows)
รองรับการอ่านข้อความ, แสดงจำนวนหน้า, เพิ่มหน้าเปล่า/แทรกหน้าใหม่, ลบหน้า และบันทึกไฟล์ใหม่
"""

from pathlib import Path
from typing import Iterable, List, Optional, Union
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import (
     DecodedStreamObject,
    DictionaryObject,
    NameObject,
)


class PDFEditor:
    """คลาสสำหรับจัดการไฟล์ PDF ด้วยไลบรารี pypdf"""

    def __init__(self, pdf_path: Optional[Union[str, Path]] = None):
        """
        เปิดไฟล์ PDF ที่มีอยู่ หรือสร้างเอกสาร PDF เปล่าหากไม่ได้ระบุพาธ

        :param pdf_path: พาธของไฟล์ PDF ต้นฉบับ (ถ้าไม่ระบุจะสร้างเอกสารใหม่)
        """
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.pages: List[PageObject] = []

        if self.pdf_path:
            if not self.pdf_path.exists():
                raise FileNotFoundError(f"ไม่พบไฟล์ PDF: {self.pdf_path}")
            reader = PdfReader(str(self.pdf_path))
            self.pages = list(reader.pages)

    def get_page_count(self) -> int:
        """คืนค่าจำนวนหน้าทั้งหมดของไฟล์ PDF"""
        return len(self.pages)

    @staticmethod
    def _extract_clean_text(page: PageObject) -> str:
        """
        ดึงข้อความจากหน้า PDF พร้อมซ่อมแซมตารางฟอนต์ /ToUnicode ที่เป็นค่าว่าง (<>) ใน PDF ภาษาไทย
        """
        try:
            resources = page.get("/Resources")
            if resources and "/Font" in resources:
                fonts = resources["/Font"].get_object()
                for font_ref in fonts.values():
                    font_obj = font_ref.get_object()
                    if "/ToUnicode" in font_obj:
                        cmap_obj = font_obj["/ToUnicode"].get_object()
                        raw_data = cmap_obj.get_data()
                        if b"<>" in raw_data:
                            fixed_stream = DecodedStreamObject()
                            fixed_stream.set_data(raw_data.replace(b"<>", b"<0e32>"))
                            font_obj[NameObject("/ToUnicode")] = fixed_stream
        except Exception:
            pass

        text = page.extract_text() or ""
        return text.replace("\u0e33\u0e32", "\u0e33").replace("\u0e4d\u0e32", "\u0e33")

    def read_text(self, page_number: Optional[int] = None) -> Union[str, List[str]]:
        """
        อ่านข้อความจากไฟล์ PDF (เลขหน้าเริ่มต้นที่ 1 สำหรับผู้ใช้)

        :param page_number: เลขหน้าที่ต้องการอ่าน (เริ่มจาก 1) หากไม่ระบุจะอ่านทุกหน้า
        :return: ข้อความของหน้าที่ระบุ (str) หรือรายการข้อความทุกหน้า (List[str])
        """
        total_pages = self.get_page_count()
        if page_number is not None:
            if not (1 <= page_number <= total_pages):
                raise ValueError(
                    f"เลขหน้าไม่ถูกต้อง ({page_number}) ไฟล์นี้มีทั้งหมด {total_pages} หน้า"
                )
            page = self.pages[page_number - 1]
            return self._extract_clean_text(page)

        return [self._extract_clean_text(page) for page in self.pages]

    def print_info_and_text(self) -> None:
        """แสดงจำนวนหน้าและข้อความในแต่ละหน้าออกทางหน้าจอ"""
        total_pages = self.get_page_count()
        source_name = self.pdf_path.name if self.pdf_path else "New Document"
        print(f"=== ข้อมูลไฟล์: {source_name} ===")
        print(f"จำนวนหน้าทั้งหมด: {total_pages} หน้า\n")

        for idx, text in enumerate(self.read_text(), start=1):
            print(f"--- หน้าที่ {idx} ---")
            cleaned = text.strip()
            print(cleaned if cleaned else "[ไม่มีข้อความในหน้านี้ / หน้าเปล่า]")
            print()

    @staticmethod
    def _add_simple_text_to_page(page: PageObject, text: str) -> None:
        """
        เพิ่มข้อความภาษาอังกฤษพื้นฐานลงบน PageObject ด้วยโครงสร้างมาตรฐานของ pypdf
        (ไม่ต้องพึ่งพาไลบรารีเสริมภายนอก)
        """
        font_dict = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        resources = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font_dict}
                )
            }
        )
        page[NameObject("/Resources")] = resources

        safe_text = (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        content_stream = DecodedStreamObject()
        content_stream.set_data(
            f"BT /F1 14 Tf 50 760 Td ({safe_text}) Tj ET".encode("latin-1", errors="replace")
        )
        page[NameObject("/Contents")] = content_stream

    def add_blank_page(
        self,
        page_number: Optional[int] = None,
        width: float = 595.0,
        height: float = 842.0,
        text: Optional[str] = None,
    ) -> None:
        """
        เพิ่มหน้าเปล่า (Blank Page) หรือหน้าใหม่เข้าไปในเอกสาร
        ขนาดเริ่มต้นคือ A4 (595 x 842 จุด)

        :param page_number: ตำแหน่งหน้าที่ต้องการแทรก (เริ่มจาก 1) หากไม่ระบุจะต่อท้ายสุด
        :param width: ความกว้างของหน้ากระดาษ (ค่าเริ่มต้น 595 = A4)
        :param height: ความสูงของหน้ากระดาษ (ค่าเริ่มต้น 842 = A4)
        :param text: ข้อความตัวอย่างที่ต้องการใส่ในหน้าใหม่ (ถ้ามี)
        """
        blank_page = PageObject.create_blank_page(width=width, height=height)
        if text:
            self._add_simple_text_to_page(blank_page, text)

        if page_number is None:
            self.pages.append(blank_page)
        else:
            if not (1 <= page_number <= self.get_page_count() + 1):
                raise ValueError(
                    f"ตำแหน่งหน้าที่ต้องการแทรกไม่ถูกต้อง: {page_number}"
                )
            self.pages.insert(page_number - 1, blank_page)

    def insert_pdf(
        self,
        other_pdf_path: Union[str, Path],
        start_at_page: Optional[int] = None,
        from_page: int = 1,
        to_page: Optional[int] = None,
    ) -> None:
        """
        แทรกหน้าจากไฟล์ PDF อื่นเข้ามาในเอกสารปัจจุบัน

        :param other_pdf_path: พาธของไฟล์ PDF ที่ต้องการนำมาแทรก
        :param start_at_page: ตำแหน่งหน้าในเอกสารปัจจุบันที่ต้องการแทรก (เริ่มจาก 1, ไม่ระบุ=ต่อท้าย)
        :param from_page: หน้าเริ่มต้นของไฟล์ที่จะนำมาแทรก (เริ่มจาก 1)
        :param to_page: หน้าสุดท้ายของไฟล์ที่จะนำมาแทรก (เริ่มจาก 1, ไม่ระบุ=ถึงหน้าสุดท้าย)
        """
        other_path = Path(other_pdf_path)
        if not other_path.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์ PDF ที่ต้องการแทรก: {other_path}")

        other_reader = PdfReader(str(other_path))
        src_total = len(other_reader.pages)
        end_page = to_page if to_page is not None else src_total

        if not (1 <= from_page <= end_page <= src_total):
            raise ValueError(
                f"ช่วงหน้าไม่ถูกต้อง ({from_page}-{end_page}) ไฟล์ต้นทางมี {src_total} หน้า"
            )

        selected_pages = other_reader.pages[from_page - 1 : end_page]

        if start_at_page is None:
            self.pages.extend(selected_pages)
        else:
            if not (1 <= start_at_page <= self.get_page_count() + 1):
                raise ValueError(
                    f"ตำแหน่งหน้าที่ต้องการแทรกไม่ถูกต้อง: {start_at_page}"
                )
            insert_idx = start_at_page - 1
            for offset, page in enumerate(selected_pages):
                self.pages.insert(insert_idx + offset, page)

    def delete_pages(self, page_numbers: Union[int, Iterable[int]]) -> None:
        """
        ลบหน้าที่ไม่ต้องการออกจากเอกสาร (ระบุเป็นเลขหน้าเดียว หรือรายการเลขหน้า เริ่มจาก 1)

        :param page_numbers: เลขหน้า เช่น 2 หรือ [1, 3]
        """
        if isinstance(page_numbers, int):
            pages_to_delete = [page_numbers]
        else:
            pages_to_delete = sorted(set(page_numbers), reverse=True)

        total_pages = self.get_page_count()
        for pno in pages_to_delete:
            if not (1 <= pno <= total_pages):
                raise ValueError(
                    f"ไม่สามารถลบหน้าที่ {pno} ได้ เนื่องจากเอกสารมี {total_pages} หน้า"
                )

        # ลบจากหน้ามากไปน้อยเพื่อไม่ให้ลำดับหน้าก่อนหน้าเลื่อน
        for pno in sorted(set(pages_to_delete), reverse=True):
            del self.pages[pno - 1]

    def highlight_and_append_text(
        self,
        keyword: str,
        append_text: str = "",
        page_number: Optional[int] = None,
        highlight_color: tuple = (1.0, 0.95, 0.35),
        append_color: tuple = (0.82, 0.08, 0.08),
        highlight_only_keyword: bool = False,
    ) -> int:
        """
        ค้นหาข้อความในหน้า PDF เพื่อระบายสีไฮไลต์ (Highlight) และเพิ่มข้อความต่อท้ายในบรรทัดเดียวกัน

        :param keyword: ข้อความหรือคำในบรรทัดที่ต้องการไฮไลต์
        :param append_text: ข้อความที่ต้องการเพิ่มต่อท้ายในบรรทัดเดียวกัน
        :param page_number: เลขหน้าที่ต้องการทำรายการ (เริ่มจาก 1, หากไม่ระบุจะค้นหาทุกหน้า)
        :param highlight_color: สีไฮไลต์ในรูปแบบ RGB (0.0 - 1.0) ค่าเริ่มต้นคือสีเหลือง
        :param append_color: สีตัวอักษรของข้อความที่เพิ่มต่อท้ายในรูปแบบ RGB (0.0 - 1.0)
        :param highlight_only_keyword: หากเป็น True จะไฮไลต์เฉพาะคำที่ค้นหา หากเป็น False จะไฮไลต์ทั้งบรรทัดนั้น
        :return: จำนวนจุดที่ถูกไฮไลต์และเพิ่มข้อความต่อท้าย
        """
        from app import apply_text_modifications_to_page, parse_page_text_groups

        target_indices = (
            [page_number - 1]
            if page_number is not None
            else list(range(self.get_page_count()))
        )
        matched_count = 0
        temp_writer = PdfWriter()

        for idx in target_indices:
            if not (0 <= idx < self.get_page_count()):
                raise ValueError(f"เลขหน้าไม่ถูกต้อง: {idx + 1}")
            page = self.pages[idx]
            groups = parse_page_text_groups(page)
            if not groups:
                continue

            new_texts = [g["original_text"] for g in groups]
            hl_configs = []
            page_matched = False

            for g in groups:
                orig = g["original_text"]
                if keyword and keyword in orig:
                    matched_count += 1
                    page_matched = True
                    hl_configs.append(
                        {
                            "highlight": True,
                            "subtext": keyword if highlight_only_keyword else "",
                            "append_text": append_text,
                            "hl_color": highlight_color,
                            "append_color": append_color,
                            "highlight_append_too": False,
                        }
                    )
                else:
                    hl_configs.append({"highlight": False})

            if page_matched:
                apply_text_modifications_to_page(
                    writer=temp_writer,
                    page=page,
                    groups=groups,
                    new_texts=new_texts,
                    highlight_configs=hl_configs,
                    extra_texts=[],
                )

        return matched_count

    @staticmethod
    def merge_pdfs(
        pdf_paths: Iterable[Union[str, Path]],
        output_path: Union[str, Path],
    ) -> Path:
        """
        รวมไฟล์ PDF หลายๆ ไฟล์เข้าเป็นไฟล์ PDF เดียวกันตามลำดับรายการที่ระบุ

        :param pdf_paths: รายการพาธของไฟล์ PDF ที่ต้องการนำมารวมกัน
        :param output_path: พาธของไฟล์ PDF ปลายทางที่รวมเสร็จแล้ว
        :return: Path ของไฟล์ PDF ที่บันทึกเสร็จแล้ว
        """
        writer = PdfWriter()
        for p in pdf_paths:
            path_obj = Path(p)
            if not path_obj.exists():
                raise FileNotFoundError(f"ไม่พบไฟล์ PDF ที่ต้องการรวม: {path_obj}")
            reader = PdfReader(str(path_obj))
            for page in reader.pages:
                writer.add_page(page)

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            writer.write(f)
        return out

    def save(self, output_path: Union[str, Path]) -> Path:
        """
        บันทึกผลลัพธ์เป็นไฟล์ PDF ใหม่ด้วย PdfWriter

        :param output_path: พาธของไฟล์ PDF ปลายทาง
        :return: Path ของไฟล์ที่บันทึกเสร็จแล้ว
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        writer = PdfWriter()
        for page in self.pages:
            writer.add_page(page)

        with open(out, "wb") as f:
            writer.write(f)

        return out

    def close(self) -> None:
        """ล้างรายการหน้าในหน่วยความจำ"""
        self.pages.clear()

    def __enter__(self) -> "PDFEditor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_sample_pdf(file_path: Union[str, Path]) -> Path:
    """ฟังก์ชันช่วยสร้างไฟล์ PDF ตัวอย่างสำหรับทดสอบโปรแกรม"""
    with PDFEditor() as editor:
        editor.add_blank_page(text="Page 1: Welcome to pypdf PDF Editor")
        editor.add_blank_page(text="Page 2: This page will be deleted in the demo")
        editor.add_blank_page(text="Page 3: Conclusion and Summary")
        return editor.save(file_path)


if __name__ == "__main__":
    sample_file = Path("sample_input.pdf")
    output_file = Path("sample_output.pdf")

    # สร้างไฟล์ตัวอย่างสำหรับทดสอบ
    create_sample_pdf(sample_file)
    print(f"สร้างไฟล์ตัวอย่าง '{sample_file}' เรียบร้อยแล้ว\n")

    # ตัวอย่างการใช้งานครบทั้ง 4 ฟังก์ชัน
    with PDFEditor(sample_file) as pdf:
        # 1. อ่านข้อความและแสดงจำนวนหน้าของไฟล์ PDF
        print("1) อ่านข้อมูลจากไฟล์ต้นฉบับ:")
        pdf.print_info_and_text()

        # 2. เพิ่มหน้าเปล่า (Blank Page) แทรกที่หน้าที่ 2 และเพิ่มหน้าใหม่ท้ายสุด
        print("2) แทรกหน้าเปล่าที่ตำแหน่งหน้าที่ 2 และเพิ่มหน้าใหม่ท้ายเอกสาร...")
        pdf.add_blank_page(page_number=2)  # หน้าเปล่าแทรกที่หน้า 2
        pdf.add_blank_page(text="Appendix: Newly inserted page at the end")

        # 3. ลบหน้าที่ไม่ต้องการ (เช่น หน้าที่ 3 ซึ่งเดิมคือหน้าที่ 2 ก่อนแทรกหน้าเปล่า)
        print("3) ลบหน้าที่ 3 ออกจากเอกสาร...\n")
        pdf.delete_pages(3)

        # 4. บันทึกผลลัพธ์เป็นไฟล์ PDF ใหม่
        saved_path = pdf.save(output_file)
        print(f"4) บันทึกไฟล์ใหม่สำเร็จที่: {saved_path.resolve()}\n")

    # ตรวจสอบผลลัพธ์จากไฟล์ใหม่ที่บันทึกไว้
    with PDFEditor(output_file) as result_pdf:
        print("ตรวจสอบผลลัพธ์ของไฟล์ PDF ใหม่:")
        result_pdf.print_info_and_text()
