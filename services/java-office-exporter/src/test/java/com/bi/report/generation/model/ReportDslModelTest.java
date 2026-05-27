package com.bi.report.generation.model;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.InputStream;

import static org.junit.jupiter.api.Assertions.*;

class ReportDslModelTest {
    private ObjectMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = new ObjectMapper();
    }

    @Test
    void testDeserializeFlowReport() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            assertNotNull(is, "showcase-flow.json not found");
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);

            assertNotNull(model);
            assertEquals("flow", model.structureType);
            assertNotNull(model.basicInfo);
            assertEquals("showcase-flow-001", model.basicInfo.id);
            assertEquals("完整导出功能演示报告", model.basicInfo.title);
            assertEquals("Word文档导出测试", model.basicInfo.subTitle);
            assertEquals("1.0", model.basicInfo.schemaVersion);
            assertEquals("success", model.basicInfo.status);
            assertEquals("2026-05-26", model.basicInfo.createdAt);
            assertEquals("测试系统", model.basicInfo.creator);
            assertEquals("报告系统导出测试", model.basicInfo.header);
            assertEquals("© 2026 Report System", model.basicInfo.footer);

            assertNotNull(model.cover);
            assertEquals("完整导出功能演示", model.cover.title);
            assertEquals("报告系统", model.cover.author);
            assertEquals("2026年5月26日", model.cover.date);

            assertNotNull(model.signaturePage);
            assertEquals("签署页", model.signaturePage.title);
            assertEquals(2, model.signaturePage.signers.size());
            assertEquals("张三", model.signaturePage.signers.get(0).name);
            assertEquals("项目经理", model.signaturePage.signers.get(0).role);

            assertNotNull(model.catalogs);
            assertEquals(4, model.catalogs.size());
            assertEquals("第一章 文本与Markdown", model.catalogs.get(0).name);
            assertEquals("第二章 表格展示", model.catalogs.get(1).name);
            assertEquals("第三章 原生图表", model.catalogs.get(2).name);
            assertEquals("第四章 降级图表", model.catalogs.get(3).name);

            assertNotNull(model.summary);
            assertEquals("report-summary", model.summary.id);
            assertTrue(model.summary.overview.contains("完整展示"));

            assertNotNull(model.layout);
            assertEquals("A4", model.layout.type);
            assertTrue(model.layout.autoLayout);
            assertNotNull(model.layout.grid);
            assertEquals(12, model.layout.grid.cols);

            assertNotNull(model.reportMeta);
            assertTrue(model.reportMeta.containsKey("sec-text"));
        }
    }

    @Test
    void testDeserializePagedReport() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-paged.json")) {
            assertNotNull(is, "showcase-paged.json not found");
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);

            assertNotNull(model);
            assertEquals("paged", model.structureType);
            assertNotNull(model.basicInfo);
            assertEquals("showcase-paged-001", model.basicInfo.id);
            assertEquals("PPT导出功能演示", model.basicInfo.title);

            assertNotNull(model.cover);
            assertEquals("PPT导出功能演示", model.cover.title);

            assertNotNull(model.backCover);
            assertEquals("谢谢观看", model.backCover.text);

            assertNotNull(model.content);
            assertEquals(4, model.content.size());

            assertTrue(model.content.get(0) instanceof ReportSlide);
            ReportSlide slide1 = (ReportSlide) model.content.get(0);
            assertEquals("slide-intro", slide1.id);
            assertEquals("简介", slide1.title);

            assertTrue(model.content.get(1) instanceof ReportSlideSection);
            ReportSlideSection section = (ReportSlideSection) model.content.get(1);
            assertEquals("section-data", section.id);
            assertEquals("数据展示", section.title);
            assertEquals(2, section.slides.size());

            assertNotNull(model.summary);
            assertTrue(model.summary.overview.contains("分页报告"));
        }
    }

    @Test
    void testComponentPolymorphicDeserialization() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);

            ReportSection textSection = model.catalogs.get(0).sections.get(0);
            assertEquals(2, textSection.components.size());

            assertTrue(textSection.components.get(0) instanceof TextComponent);
            TextComponent textComp = (TextComponent) textSection.components.get(0);
            assertEquals("text-1", textComp.id);
            assertEquals("text", textComp.type);
            assertNotNull(textComp.dataProperties);
            assertEquals("普通文本标题", textComp.dataProperties.title);

            assertTrue(textSection.components.get(1) instanceof MarkdownComponent);
            MarkdownComponent mdComp = (MarkdownComponent) textSection.components.get(1);
            assertEquals("markdown-1", mdComp.id);
            assertEquals("markdown", mdComp.type);
            assertTrue(mdComp.dataProperties.content.contains("# Markdown标题1"));
        }
    }

    @Test
    void testTableComponentDeserialization() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);

            ReportSection tableSection = model.catalogs.get(1).sections.get(0);
            assertEquals(2, tableSection.components.size());

            assertTrue(tableSection.components.get(0) instanceof TableComponent);
            TableComponent tableComp = (TableComponent) tableSection.components.get(0);
            assertEquals("table-1", tableComp.id);
            assertEquals("table", tableComp.type);
            assertEquals("销售数据表", tableComp.dataProperties.title);
            assertEquals(4, tableComp.dataProperties.columns.size());
            assertEquals("month", tableComp.dataProperties.columns.get(0).key);
            assertEquals("月份", tableComp.dataProperties.columns.get(0).title);
            assertEquals(5, tableComp.dataProperties.data.size());
            assertEquals(1, tableComp.dataProperties.mergeRows.size());
            assertEquals(0, tableComp.dataProperties.mergeRows.get(0).startRowIndex);
            assertEquals(2, tableComp.dataProperties.mergeRows.get(0).rowSpan);
        }
    }

    @Test
    void testCompositeTableDeserialization() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);

            ReportSection tableSection = model.catalogs.get(1).sections.get(0);
            assertTrue(tableSection.components.get(1) instanceof CompositeTableComponent);
            CompositeTableComponent composite = (CompositeTableComponent) tableSection.components.get(1);
            assertEquals("composite-1", composite.id);
            assertEquals("compositeTable", composite.type);
            assertEquals("复合表 - 多产品对比", composite.dataProperties.title);
            assertEquals(2, composite.tables.size());
            assertEquals("sub-table-1", composite.tables.get(0).id);
            assertEquals("子表1 - 产品A", composite.tables.get(0).dataProperties.title);
        }
    }

    @Test
    void testChartComponentDeserialization() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);

            ReportSection lineSection = model.catalogs.get(2).sections.get(0);
            assertTrue(lineSection.components.get(0) instanceof ChartComponent);
            ChartComponent lineChart = (ChartComponent) lineSection.components.get(0);
            assertEquals("chart-line", lineChart.id);
            assertEquals("chart", lineChart.type);
            assertEquals("月度趋势图", lineChart.dataProperties.title);
            assertEquals(3, lineChart.dataProperties.columns.size());
            assertEquals(5, lineChart.dataProperties.data.size());
            assertEquals(2, lineChart.dataProperties.series.size());
            assertEquals("line", lineChart.dataProperties.series.get(0).get("type"));
        }
    }
}
