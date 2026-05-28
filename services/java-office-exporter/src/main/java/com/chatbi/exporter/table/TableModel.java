package com.chatbi.exporter.table;

import java.util.Collections;
import java.util.List;

/**
 * 表格语义模型。
 * <p>
 * headerRows/bodyRows 均按“完整矩阵”表达；
 * 合并单元格由锚点 + hidden 占位实现，便于跨端一致渲染。
 * </p>
 */
public record TableModel(
        String title,
        List<TableColumn> columns,
        List<List<TableCell>> headerRows,
        List<List<TableCell>> bodyRows,
        boolean repeatHeader,
        boolean zebra
) {
    /**
     * 复制并冻结输入集合，避免后续渲染阶段误改源数据。
     */
    public TableModel {
        columns = columns == null ? Collections.emptyList() : List.copyOf(columns);
        headerRows = headerRows == null ? Collections.emptyList() : copyGrid(headerRows);
        bodyRows = bodyRows == null ? Collections.emptyList() : copyGrid(bodyRows);
    }

    /**
     * @return 列总数
     */
    public int columnCount() {
        return columns.size();
    }

    /**
     * @return 表头行数
     */
    public int headerRowCount() {
        return headerRows.size();
    }

    /**
     * @return 数据行数
     */
    public int bodyRowCount() {
        return bodyRows.size();
    }

    /**
     * @return 表格总行数（表头 + 数据）
     */
    public int totalRowCount() {
        return headerRowCount() + bodyRowCount();
    }

    private static List<List<TableCell>> copyGrid(List<List<TableCell>> rows) {
        return rows.stream().map(row -> row == null ? Collections.<TableCell>emptyList() : List.copyOf(row)).toList();
    }
}
