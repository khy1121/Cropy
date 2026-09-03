import { DiagnoseForm } from "@/components/DiagnoseForm";

export default function HomePage() {
  return (
    <>
      <section className="mb-5 md:mb-7">
        <h1 className="text-[1.4375rem] font-extrabold leading-snug tracking-tight text-ink md:text-[1.75rem]">
          사진 한 장으로{" "}
          <br className="md:hidden" />
          병해충을 진단하세요
        </h1>
        <p className="mt-1.5 text-sm leading-relaxed text-muted md:text-base">
          잎이나 과실을 촬영하면 AI가 병해충과 방제법을 알려드려요.
        </p>
      </section>
      <DiagnoseForm />
    </>
  );
}
