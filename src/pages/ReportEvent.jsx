import { useEffect, useState } from "react";
import { base44 } from "@/api/base44Client";
import { useLanguage } from "@/lib/LanguageContext";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { CheckCircle2 } from "lucide-react";

export default function ReportEvent() {
  const { t } = useLanguage();
  const [areas, setAreas] = useState([]);
  const [areaKey, setAreaKey] = useState("");
  const [flooded, setFlooded] = useState("yes");
  const [eventDate, setEventDate] = useState("");
  const [description, setDescription] = useState("");
  const [photoFile, setPhotoFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    base44.entities.Area.list().then(setAreas);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!areaKey) return;
    setSubmitting(true);
    let photo_url;
    if (photoFile) {
      const { file_url } = await base44.integrations.Core.UploadPublicFile({ file: photoFile });
      photo_url = file_url;
    }
    const [area_name, country] = areaKey.split("|");
    await base44.entities.PostEventReport.create({
      area_name, country, flooded: flooded === "yes", event_date: eventDate || undefined, description, photo_url, status: "pending",
    });
    setSubmitting(false);
    setDone(true);
  };

  if (done) {
    return (
      <div className="max-w-md mx-auto px-5 py-20 text-center">
        <CheckCircle2 className="w-12 h-12 text-teal-700 mx-auto mb-4" />
        <p className="text-slate-700 leading-relaxed">{t("report_success")}</p>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto px-5 py-14">
      <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{t("report_title")}</h1>
      <p className="text-slate-600 mt-2 leading-relaxed">{t("report_subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-5">
        <div>
          <Label>{t("report_area_label")}</Label>
          <Select value={areaKey} onValueChange={setAreaKey}>
            <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
            <SelectContent>
              {areas.map((a) => (
                <SelectItem key={a.id} value={`${a.name}|${a.country}`}>{a.name}, {a.country}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>{t("report_flooded_label")}</Label>
          <RadioGroup value={flooded} onValueChange={setFlooded} className="flex gap-6 mt-2">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="flood-yes" />
              <Label htmlFor="flood-yes" className="font-normal">{t("report_flooded_yes")}</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="flood-no" />
              <Label htmlFor="flood-no" className="font-normal">{t("report_flooded_no")}</Label>
            </div>
          </RadioGroup>
        </div>

        <div>
          <Label>{t("report_date_label")}</Label>
          <Input type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} className="mt-1.5" />
        </div>

        <div>
          <Label>{t("report_description_label")}</Label>
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1.5" rows={4} />
        </div>

        <div>
          <Label>{t("report_photo_label")}</Label>
          <Input type="file" accept="image/*" onChange={(e) => setPhotoFile(e.target.files?.[0] || null)} className="mt-1.5" />
        </div>

        <Button type="submit" disabled={submitting || !areaKey} size="lg" className="bg-teal-800 hover:bg-teal-900 w-full">
          {submitting ? t("report_submitting") : t("report_submit")}
        </Button>
      </form>
    </div>
  );
}