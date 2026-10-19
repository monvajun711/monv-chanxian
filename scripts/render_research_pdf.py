#!/usr/bin/env python3
"""Render a validated research evidence pack to a Chinese-language PDF."""
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle, PageBreak, KeepTogether,
                                Image)
from reportlab.graphics.shapes import Drawing, String, Line, Rect


NAVY = colors.HexColor("#14283F")
TEAL = colors.HexColor("#138A8A")
PALE = colors.HexColor("#EAF2F5")
INK = colors.HexColor("#273746")
MUTED = colors.HexColor("#637381")


def build(json_path, output):
    d = json.loads(Path(json_path).read_text(encoding="utf-8"))
    metric_map={m["id"]:m for m in d.get("metrics",[])}
    def expand(text):
        def replace(match):
            m=metric_map[match.group(1)]
            value=f"{float(m['value']):g}" if isinstance(m["value"],(int,float)) else str(m["value"])
            return f"{value} {m['unit']}"
        return re.sub(r"\{\{metric:([\w.-]+)\}\}",replace,str(text))
    font_path = r"C:\Windows\Fonts\msyh.ttc"
    pdfmetrics.registerFont(TTFont("Chinese", font_path, subfontIndex=0))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitleCN", fontName="Chinese", fontSize=24, leading=32, textColor=NAVY, alignment=TA_LEFT, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubCN", fontName="Chinese", fontSize=11, leading=17, textColor=MUTED, spaceAfter=6))
    styles.add(ParagraphStyle(name="H1CN", fontName="Chinese", fontSize=16, leading=22, textColor=NAVY, spaceBefore=10, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name="H2CN", fontName="Chinese", fontSize=11, leading=16, textColor=TEAL, spaceBefore=5, spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="BodyCN", fontName="Chinese", fontSize=9, leading=14, textColor=INK, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallCN", fontName="Chinese", fontSize=7.4, leading=10, textColor=MUTED, spaceAfter=3, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="CellCN", fontName="Chinese", fontSize=8, leading=11, textColor=INK, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="CellHeadCN", fontName="Chinese", fontSize=8, leading=11, textColor=colors.white, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="CalloutCN", fontName="Chinese", fontSize=10, leading=16, textColor=NAVY, backColor=PALE, borderPadding=8, spaceBefore=4, spaceAfter=8))
    class Doc(BaseDocTemplate):
        def __init__(self, filename):
            super().__init__(filename, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=20*mm, bottomMargin=18*mm, title=d["title"], author="魔女缠线研究工作流")
            frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id="normal")
            self.addPageTemplates([PageTemplate(id="main",frames=[frame],onPage=self.decorate)])
        def decorate(self, canvas, doc):
            w,h=A4
            canvas.saveState()
            canvas.setFillColor(NAVY); canvas.rect(0,h-7*mm,w,7*mm,fill=1,stroke=0)
            canvas.setFont("Chinese",7.5); canvas.setFillColor(MUTED)
            canvas.drawString(18*mm,10*mm,d.get("short_title", d["title"]))
            canvas.drawRightString(w-18*mm,10*mm,f"研究快照 | {d['as_of'][:10]} | {doc.page}")
            canvas.restoreState()
    story=[]
    story += [Spacer(1,24*mm), Paragraph(escape(d["title"]),styles["CoverTitleCN"]), Paragraph(escape(d.get("subtitle","公开资料研究样例")),styles["SubCN"]), Spacer(1,5*mm)]
    meta=[[Paragraph("标的",styles["CellCN"]),Paragraph(escape(d["instrument"]),styles["CellCN"])],[Paragraph("数据时点",styles["CellCN"]),Paragraph(escape(d["as_of"]),styles["CellCN"])],[Paragraph("用途",styles["CellCN"]),Paragraph(escape(d.get("purpose","研究示例；不构成个人化投资建议")),styles["CellCN"])]]
    t=Table(meta,colWidths=[27*mm,145*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),PALE),("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#D5E0E7")),("INNERGRID",(0,0),(-1,-1),0.3,colors.HexColor("#D5E0E7")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)])); story += [t,Spacer(1,8*mm)]
    story += [Paragraph(escape(d.get("cover_note","本报告使用可追溯公开资料；行情不是盘中实时行情。")),styles["CalloutCN"]),Spacer(1,4*mm)]
    if d.get("executive_summary"):
        story += [Paragraph("核心结论",styles["H1CN"]),Paragraph(escape(expand(d["executive_summary"])),styles["BodyCN"])]
    if d.get("metrics_table"):
        rows=[[Paragraph(x,styles["CellHeadCN"]) for x in d["metrics_table"]["headers"]]]
        for row in d["metrics_table"]["rows"]: rows.append([Paragraph(escape(expand(x)),styles["CellCN"]) for x in row])
        widths=d["metrics_table"].get("widths",[40,33,37,62])
        tb=Table(rows,colWidths=[x*mm for x in widths],repeatRows=1,hAlign="LEFT")
        tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#D5E0E7")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)])); story += [tb,Spacer(1,5*mm)]
    if d.get("disclosures_on_cover") and d.get("disclosures"):
        story.append(Paragraph("重要限制",styles["H2CN"]))
        for s in d["disclosures"]: story.append(Paragraph(escape(s),styles["SmallCN"]))
    if d.get("page_break_before_sections"):
        page_breaks=set(d["page_break_before_sections"])
    else:
        page_breaks=set()
    for sec in d.get("sections",[]):
        if sec["title"] in page_breaks:
            story.append(PageBreak())
        story.append(Paragraph(escape(sec["title"]),styles["H1CN"] if sec.get("level",1)==1 else styles["H2CN"]))
        for p in sec.get("paragraphs",[]): story.append(Paragraph(escape(expand(p)),styles["BodyCN"]))
        if sec.get("bullets"):
            for b in sec["bullets"]: story.append(Paragraph("• " + escape(expand(b)),styles["BodyCN"]))
    if d.get("charts"):
        story.append(Paragraph("图表与证据",styles["H1CN"]))
        for c in d["charts"]:
            if c.get("series"):
                drawing=Drawing(480,155)
                plot=c["series"]
                vals=[float(x[1]) for x in plot["data"]]
                lo=0 if plot.get("zero_baseline") else min(vals); hi=max(vals); span=max(hi-lo,1e-9)
                left,bottom,width,height=58,28,390,92
                drawing.add(Rect(left,bottom,width,height,fillColor=colors.white,strokeColor=colors.HexColor("#D5E0E7")))
                for j in range(5):
                    y=bottom+j*height/4
                    v=lo+j*span/4
                    drawing.add(Line(left,y,left+width,y,strokeColor=colors.HexColor("#E4EBF0"),strokeWidth=.5))
                    drawing.add(String(4,y-3,f"{v:.2f}",fontName="Chinese",fontSize=7,fillColor=MUTED))
                pts=[]
                for i,(label,value) in enumerate(plot["data"]):
                    x=left+i*width/max(1,len(vals)-1); y=bottom+(float(value)-lo)/span*height; pts.append((x,y))
                for a,b in zip(pts,pts[1:]): drawing.add(Line(a[0],a[1],b[0],b[1],strokeColor=TEAL,strokeWidth=2))
                for x,y in pts: drawing.add(Rect(x-2,y-2,4,4,fillColor=TEAL,strokeColor=TEAL))
                for i in sorted(set([0,len(vals)//2,len(vals)-1])):
                    x=pts[i][0]; label=plot["data"][i][0]
                    tick=label[5:] if len(label)>=10 and label[4]=="-" else label
                    drawing.add(String(x-14,12,tick,fontName="Chinese",fontSize=7,fillColor=MUTED))
                drawing.add(String(left,bottom+height+8,f"单位：{plot.get('unit','')} | 来源：{plot.get('source_label','')}",fontName="Chinese",fontSize=7,fillColor=MUTED))
                story += [Paragraph(escape(c["title"]),styles["H2CN"]),drawing,Paragraph(escape(c.get("caption","")),styles["SmallCN"])]
            elif c.get("image"):
                story += [Paragraph(escape(c["title"]),styles["H2CN"]),Image(c["image"],width=166*mm,height=76*mm),Paragraph(escape(c.get("caption","")),styles["SmallCN"])]
    if d.get("disclosures") and not d.get("disclosures_on_cover"):
        story.append(Paragraph("重要限制",styles["H1CN"]))
        for s in d["disclosures"]: story.append(Paragraph(escape(s),styles["SmallCN"]))
    if d.get("sources"):
        story.append(Paragraph("来源与口径",styles["H1CN"]))
        for src in d["sources"]:
            url=escape(src["url"], {"\"": "&quot;"})
            link=f'<link href="{url}" color="#138A8A">{url}</link>'
            story.append(Paragraph(f"[{escape(src['id'])}] {escape(src['title'])}；披露/数据日期：{escape(src.get('published_at',''))}；{link}",styles["SmallCN"]))
    Doc(output).build(story)


if __name__ == "__main__":
    if len(sys.argv)!=3: raise SystemExit("usage: render_research_pdf.py REPORT.json OUTPUT.pdf")
    build(sys.argv[1],sys.argv[2])
