import { Suspense } from "react";
import { DiagnoseForm } from "@/components/DiagnoseForm";

export default function HomePage() {
  return (
    <Suspense>
      <DiagnoseForm />
    </Suspense>
  );
}
