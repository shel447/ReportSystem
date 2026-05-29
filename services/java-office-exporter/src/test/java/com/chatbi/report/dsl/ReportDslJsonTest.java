package com.chatbi.report.dsl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ReportDslJsonTest {
    @Test
    void readsFlowReportWithComponentSeriesLayoutAndValueFormatPolymorphism() throws Exception {
        Report report = ReportDslJson.read("""
                {
                  "structureType": "flow",
                  "unknownRoot": "ignored",
                  "basicInfo": {
                    "id": "rpt_flow",
                    "schemaVersion": "1.0.0",
                    "status": "Success",
                    "reportType": "Word",
                    "title": "legacy ignored title",
                    "createdAt": "2026-05-29T10:00:00+08:00",
                    "updatedAt": "2026-05-29T10:00:00+08:00",
                    "parameters": {},
                    "unknownBasicInfo": "ignored"
                  },
                  "catalogs": [
                    {
                      "id": "catalog_main",
                      "name": "主目录",
                      "sections": [
                        {
                          "id": "section_main",
                          "title": "主章节",
                          "components": [
                            {
                              "id": "text_1",
                              "type": "text",
                              "layout": {"type": "grid", "gx": 0, "gy": 0, "gw": 12, "gh": 2},
                              "dataProperties": {"dataType": "static", "content": "正文", "ignored": true}
                            },
                            {
                              "id": "table_1",
                              "type": "table",
                              "layout": {"type": "flow"},
                              "dataProperties": {
                                "dataType": "static",
                                "columns": [
                                  {
                                    "key": "date",
                                    "title": "日期",
                                    "uiConfig": {"valueFormat": {"type": "time", "format": "yyyy-MM-dd"}}
                                  },
                                  {
                                    "key": "ratio",
                                    "title": "占比",
                                    "uiConfig": {
                                      "displayPriority": "low",
                                      "valueFormat": {"type": "percentage", "decimal": 2, "unit": "%"},
                                      "conditionalFormat": {
                                        "rules": [
                                          {
                                            "when": {"op": "lt", "value": 0.9},
                                            "style": {"textTone": "warning", "fontWeight": "bold"}
                                          },
                                          {
                                            "when": {"op": "between", "min": 0.9, "max": 1.0},
                                            "style": {"textTone": "success"}
                                          }
                                        ]
                                      }
                                    }
                                  },
                                  {
                                    "key": "has_risk",
                                    "title": "是否风险",
                                    "type": "boolean",
                                    "uiConfig": {
                                      "displayPriority": 1,
                                      "valueFormat": {
                                        "type": "enum",
                                        "enum": [
                                          {"value": true, "label": "是"},
                                          {"value": false, "label": "否"}
                                        ]
                                      }
                                    },
                                    "lineageTracing": {
                                      "sources": [
                                        {
                                          "dataSourceName": "dw",
                                          "field": "has_risk",
                                          "businessName": "risk flag",
                                          "businessName_cn": "风险标记",
                                          "enumValues": "[{\\"value\\":true,\\"label\\":\\"是\\"}]",
                                          "ui": "{\\"displayPriority\\":\\"high\\"}"
                                        }
                                      ]
                                    }
                                  },
                                  {
                                    "key": "traffic",
                                    "title": "流量",
                                    "uiConfig": {"valueFormat": {"type": "bitRate", "decimal": 1, "unit": "Mbps"}}
                                  },
                                  {
                                    "key": "capacity",
                                    "title": "容量",
                                    "uiConfig": {"valueFormat": {"type": "unit", "decimal": 0, "unit": "GB"}}
                                  }
                                ],
                                "data": [{"date": "2026-05-28", "ratio": 0.93, "has_risk": false, "traffic": 12.3, "capacity": 512}]
                              }
                            },
                            {
                              "id": "chart_1",
                              "type": "chart",
                              "layout": {"type": "absolute", "x": 10, "y": 20, "w": 300, "h": 180},
                              "options": {
                                "responsive": {"enabled": true}
                              },
                              "advanceProperties": {
                                "responsive": {
                                  "levels": [{"size": "normal", "maxWidth": 960}],
                                  "aspectRatio": 1.6,
                                  "minHeight": 260
                                },
                                "xAxisLabelMode": "truncate",
                                "sqlExplanation": "select trend data"
                              },
                              "dataProperties": {
                                "dataType": "static",
                                "columns": [{"key": "x", "title": "X"}, {"key": "y", "title": "Y"}],
                                "data": [{"x": "A", "y": 1}],
                                "series": [
                                  {"type": "line", "subType": "area", "name": "line", "encode": {"x": "x", "y": "y"}},
                                  {"type": "bar", "subType": "horizontal", "name": "bar", "encode": {"x": "x", "y": "y"}},
                                  {"type": "pie", "subType": "ring", "name": "pie", "encode": {"name": "x", "value": "y"}},
                                  {"type": "scatter", "name": "scatter", "encode": {"x": "x", "y": "y"}},
                                  {"type": "radar", "name": "radar", "encode": {"name": "x", "value": "y"}},
                                  {"type": "gauge", "name": "gauge", "encode": {"value": "y"}},
                                  {"type": "candlestick", "name": "k", "encode": {"open": "o", "close": "c", "low": "l", "high": "h"}}
                                ]
                              }
                            },
                            {
                              "id": "markdown_1",
                              "type": "markdown",
                              "dataProperties": {"dataType": "static", "content": "**Markdown**"}
                            },
                            {
                              "id": "composite_1",
                              "type": "compositeTable",
                              "dataProperties": {"dataType": "static"},
                              "tables": [
                                {
                                  "id": "inner_table",
                                  "type": "table",
                                  "dataProperties": {"dataType": "static", "columns": [], "data": []}
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  ],
                  "layout": {"type": "grid"}
                }
                """);

        assertEquals(StructureType.FLOW, report.structureType);
        assertEquals(Status.SUCCESS, report.basicInfo.status);
        Section section = report.catalogs.getFirst().sections.getFirst();
        assertInstanceOf(TextComponent.class, section.components.get(0));
        assertInstanceOf(TableComponent.class, section.components.get(1));
        assertInstanceOf(ChartComponent.class, section.components.get(2));
        assertInstanceOf(MarkdownComponent.class, section.components.get(3));
        assertInstanceOf(CompositeTable.class, section.components.get(4));

        TextComponent text = (TextComponent) section.components.getFirst();
        assertInstanceOf(GridLayout.class, text.layout);
        TableComponent table = (TableComponent) section.components.get(1);
        assertInstanceOf(FlowLayout.class, table.layout);
        assertInstanceOf(TimeValueFormat.class, table.dataProperties.columns.getFirst().uiConfig.valueFormat);
        assertInstanceOf(NumericValueFormat.class, table.dataProperties.columns.get(1).uiConfig.valueFormat);
        assertEquals(FieldType.BOOLEAN, table.dataProperties.columns.get(2).type);
        assertEquals(1, table.dataProperties.columns.get(2).uiConfig.displayPriority);
        assertInstanceOf(EnumValueFormat.class, table.dataProperties.columns.get(2).uiConfig.valueFormat);
        assertEquals("dw", table.dataProperties.columns.get(2).lineageTracing.sources.getFirst().dataSourceName);
        assertEquals("[{\"value\":true,\"label\":\"是\"}]", table.dataProperties.columns.get(2).lineageTracing.sources.getFirst().enumValues);
        assertEquals("{\"displayPriority\":\"high\"}", table.dataProperties.columns.get(2).lineageTracing.sources.getFirst().ui);
        assertEquals("warning", table.dataProperties.columns.get(1).uiConfig.conditionalFormat.rules.getFirst().style.textTone);
        assertInstanceOf(NumericValueFormat.class, table.dataProperties.columns.get(3).uiConfig.valueFormat);
        assertEquals(ValueFormatType.BIT_RATE, ((NumericValueFormat) table.dataProperties.columns.get(3).uiConfig.valueFormat).type);
        assertEquals(ValueFormatType.UNIT, ((NumericValueFormat) table.dataProperties.columns.get(4).uiConfig.valueFormat).type);
        ChartComponent chart = (ChartComponent) section.components.get(2);
        assertInstanceOf(AbsoluteLayout.class, chart.layout);
        assertEquals("truncate", chart.advanceProperties.xAxisLabelMode);
        assertEquals("select trend data", chart.advanceProperties.sqlExplanation);
        assertEquals(ResponsiveSize.NORMAL, chart.advanceProperties.responsive.levels.getFirst().size);
        assertInstanceOf(LineSeries.class, chart.dataProperties.series.get(0));
        assertInstanceOf(BarSeries.class, chart.dataProperties.series.get(1));
        assertInstanceOf(PieSeries.class, chart.dataProperties.series.get(2));
        assertInstanceOf(ScatterSeries.class, chart.dataProperties.series.get(3));
        assertInstanceOf(RadarSeries.class, chart.dataProperties.series.get(4));
        assertInstanceOf(GaugeSeries.class, chart.dataProperties.series.get(5));
        assertInstanceOf(CandlestickSeries.class, chart.dataProperties.series.get(6));

        JsonNode serialized = new ObjectMapper().readTree(ReportDslJson.write(report));
        assertEquals("flow", serialized.path("structureType").asText());
        assertEquals("Success", serialized.path("basicInfo").path("status").asText());
        assertFalse(serialized.path("basicInfo").has("title"));
        assertFalse(serialized.path("basicInfo").has("createdAt"));
        assertFalse(serialized.path("basicInfo").has("updatedAt"));
        assertFalse(serialized.path("basicInfo").has("parameters"));
        assertEquals("text", serialized.path("catalogs").get(0).path("sections").get(0).path("components").get(0).path("type").asText());
        assertFalse(serialized.path("catalogs").get(0).path("sections").get(0).path("components").get(2).has("options"));
        assertEquals("normal", serialized.path("catalogs").get(0).path("sections").get(0).path("components").get(2)
                .path("advanceProperties").path("responsive").path("levels").get(0).path("size").asText());
        assertEquals("line", serialized.path("catalogs").get(0).path("sections").get(0).path("components").get(2)
                .path("dataProperties").path("series").get(0).path("type").asText());
    }

    @Test
    void readsPagedContentAsSlidesAndSlideSections() throws Exception {
        Report report = ReportDslJson.read("""
                {
                  "structureType": "paged",
                  "basicInfo": {"id": "rpt_paged", "schemaVersion": "1.0.0"},
                  "content": [
                    {
                      "id": "slide_direct",
                      "title": "直接页面",
                      "description": "legacy ignored description",
                      "components": [
                        {"id": "text_slide", "type": "text", "dataProperties": {"dataType": "static", "content": "Slide"}}
                      ]
                    },
                    {
                      "id": "section_group",
                      "type": "section",
                      "title": "分页章节",
                      "description": "legacy ignored section description",
                      "slides": [
                        {
                          "id": "slide_nested",
                          "title": "嵌套页面",
                          "components": [
                            {"id": "text_nested", "type": "text", "dataProperties": {"dataType": "static", "content": "Nested"}}
                          ]
                        }
                      ]
                    }
                  ]
                }
                """);

        assertInstanceOf(Slide.class, report.content.get(0));
        assertInstanceOf(SlideSection.class, report.content.get(1));
        Slide slide = (Slide) report.content.getFirst();
        assertInstanceOf(TextComponent.class, slide.components.getFirst());
        SlideSection section = (SlideSection) report.content.get(1);
        assertEquals(SlideSectionType.SECTION, section.type);
        assertInstanceOf(TextComponent.class, section.slides.getFirst().components.getFirst());
        assertTrue(ReportDslJson.write(report).contains("\"type\":\"section\""));
    }
}
