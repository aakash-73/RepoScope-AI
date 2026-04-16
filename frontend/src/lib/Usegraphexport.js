import { toPng, toSvg } from "html-to-image";
import { useReactFlow } from "@xyflow/react";

export function useGraphExport() {
    const { getViewport, setViewport, fitView } = useReactFlow();

    async function exportGraph({ format = "png", scale = 2, repoName = "graph" }) {
        const rfWrapper = document.querySelector(".react-flow__renderer");
        if (!rfWrapper) throw new Error("ReactFlow renderer not found in DOM.");

        const prevViewport = getViewport();

        await fitView({ padding: 0.08, duration: 0 });
        await new Promise((r) => setTimeout(r, 120));

        const pixelRatio = scale;

        try {
            let dataUrl;

            const commonOpts = {
                backgroundColor: "#121212",
                pixelRatio,
                skipFonts: false,
                filter: (node) => {
                    if (node?.classList?.contains("react-flow__controls")) return false;
                    if (node?.classList?.contains("react-flow__minimap")) return false;
                    if (node?.classList?.contains("react-flow__panel")) return false;
                    return true;
                },
            };

            if (format === "svg") {
                dataUrl = await toSvg(rfWrapper, commonOpts);
            } else {
                dataUrl = await toPng(rfWrapper, commonOpts);
            }

            const link = document.createElement("a");
            const ts = new Date().toISOString().slice(0, 10);
            link.download = `${repoName}-graph-${ts}.${format}`;
            link.href = dataUrl;
            link.click();
        } finally {
            setViewport(prevViewport, { duration: 300 });
        }
    }

    return exportGraph;
}