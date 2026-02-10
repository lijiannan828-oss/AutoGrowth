import type { ReactNode } from "react";
import { PipelineSubnav } from "@/components/pipeline/PipelineSubnav";
import { ZipDownloadProvider } from "@/context/ZipDownloadContext";
import { ZipDownloadCard } from "@/components/pipeline/ZipDownloadCard";

export default function PipelineLayout({ children }: { children: ReactNode }) {
  return (
    <ZipDownloadProvider>
      <section className="flex-1 flex flex-col relative">
        <PipelineSubnav />
        <div className="flex-1">{children}</div>
        <ZipDownloadCard />
      </section>
    </ZipDownloadProvider>
  );
}


