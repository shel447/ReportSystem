package report.system.exporter;

import com.fasterxml.jackson.databind.ObjectMapper;
import report.system.exporter.core.ExportRequest;
import report.system.exporter.docx.ReportDocxExporter;
import report.system.exporter.model.ReportDslModel;
import report.system.exporter.pptx.ReportPptxExporter;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class ShowcaseGenerator {

    public static void main(String[] args) throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        Path outDir = Path.of("showcase-out");
        Files.createDirectories(outDir);

        try (InputStream flowIs = ShowcaseGenerator.class.getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel flowModel = mapper.readValue(flowIs, ReportDslModel.class);
            Path docxPath = outDir.resolve("showcase-flow.docx");
            new ReportDocxExporter().export(flowModel, docxPath, new ExportRequest("enterprise-light", false));
            System.out.println("DOCX generated: " + docxPath.toAbsolutePath() + " (" + Files.size(docxPath) + " bytes)");
        }

        try (InputStream pagedIs = ShowcaseGenerator.class.getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel pagedModel = mapper.readValue(pagedIs, ReportDslModel.class);
            Path pptxPath = outDir.resolve("showcase-paged.pptx");
            new ReportPptxExporter().export(pagedModel, pptxPath, new ExportRequest("enterprise-light", false));
            System.out.println("PPTX generated: " + pptxPath.toAbsolutePath() + " (" + Files.size(pptxPath) + " bytes)");
        }

        try (InputStream flowIs = ShowcaseGenerator.class.getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel flowModel = mapper.readValue(flowIs, ReportDslModel.class);
            Path docxDark = outDir.resolve("showcase-flow-dark.docx");
            new ReportDocxExporter().export(flowModel, docxDark, new ExportRequest("enterprise-dark", false));
            System.out.println("DOCX (dark) generated: " + docxDark.toAbsolutePath() + " (" + Files.size(docxDark) + " bytes)");
        }

        try (InputStream pagedIs = ShowcaseGenerator.class.getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel pagedModel = mapper.readValue(pagedIs, ReportDslModel.class);
            Path pptxDark = outDir.resolve("showcase-paged-dark.pptx");
            new ReportPptxExporter().export(pagedModel, pptxDark, new ExportRequest("enterprise-dark", false));
            System.out.println("PPTX (dark) generated: " + pptxDark.toAbsolutePath() + " (" + Files.size(pptxDark) + " bytes)");
        }

        System.out.println("\nAll showcase files generated successfully!");
    }
}
