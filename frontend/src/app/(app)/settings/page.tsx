"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { OptionSelect } from "@/components/option-select";
import { useAuthStore } from "@/stores/auth-store";
import { useChangePassword, useCurrentUser, useDeleteAccount } from "@/hooks/use-auth";
import { useMedicalProfile, useSaveMedicalProfile, useUpdateProfile } from "@/hooks/use-profile";
import { apiErrorMessage } from "@/lib/api-error";
import { joinList, primaryGoal, splitList } from "@/lib/profile";
import { ACTIVITY_LEVELS, DIET_PREFERENCES, GOALS, type MedicalProfile, type User } from "@/types";
import { KeyRound, Loader2, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";

const inputClass = "bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500";
const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

function SaveButton({ pending, label }: { pending: boolean; label: string }) {
  return (
    <Button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white" disabled={pending}>
      {pending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
      {label}
    </Button>
  );
}

function ProfileCard({ user }: { user: User }) {
  const [name, setName] = useState(user.name ?? "");
  const [age, setAge] = useState(user.age?.toString() ?? "");
  const [gender, setGender] = useState<string>(user.gender ?? "");
  const [height, setHeight] = useState(user.height?.toString() ?? "");
  const [weight, setWeight] = useState(user.weight?.toString() ?? "");
  const [activityLevel, setActivityLevel] = useState(user.activity_level ?? "");
  const [goal, setGoal] = useState(primaryGoal(user.goals));
  const updateProfile = useUpdateProfile();

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Please enter your name.");
      return;
    }
    try {
      // Unset fields are left out rather than sent empty: the API validates
      // gender and activity level against fixed lists.
      await updateProfile.mutateAsync({
        name: name.trim(),
        age: age ? parseInt(age) : undefined,
        gender: gender || undefined,
        height: height ? parseFloat(height) : undefined,
        weight: weight ? parseFloat(weight) : undefined,
        activity_level: activityLevel || undefined,
        goals: goal ? [goal] : undefined,
      });
      toast.success("Profile updated.");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Failed to update profile. Please try again."));
    }
  };

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="text-slate-200">Profile</CardTitle>
        <p className="text-sm text-slate-400">Used to calculate your calorie and macro targets.</p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-slate-300">Full Name</Label>
              <Input id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email" className="text-slate-300">Email</Label>
              <Input id="email" value={user.email} disabled className="bg-slate-800 border-slate-700 text-slate-400" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="age" className="text-slate-300">Age</Label>
              <Input id="age" type="number" min={1} max={120} value={age} onChange={(e) => setAge(e.target.value)} className={inputClass} />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Gender</Label>
              <OptionSelect
                value={gender}
                onChange={setGender}
                placeholder="Select gender"
                options={[
                  { value: "male", label: "Male" },
                  { value: "female", label: "Female" },
                  { value: "other", label: "Other" },
                ]}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="height" className="text-slate-300">Height (cm)</Label>
              <Input id="height" type="number" min={50} max={300} value={height} onChange={(e) => setHeight(e.target.value)} className={inputClass} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weight" className="text-slate-300">Weight (kg)</Label>
              <Input id="weight" type="number" min={10} max={500} step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} className={inputClass} />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Activity Level</Label>
              <OptionSelect value={activityLevel} onChange={setActivityLevel} placeholder="Select activity level" options={ACTIVITY_LEVELS} />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Health Goal</Label>
              <OptionSelect value={goal} onChange={setGoal} placeholder="Select goal" options={GOALS} />
            </div>
          </div>
          <SaveButton pending={updateProfile.isPending} label="Save Profile" />
        </form>
      </CardContent>
    </Card>
  );
}

function MedicalCard({ profile }: { profile: MedicalProfile | null }) {
  const [bloodType, setBloodType] = useState(profile?.blood_type ?? "");
  const [dietaryPreference, setDietaryPreference] = useState(profile?.dietary_preference ?? "");
  const [allergies, setAllergies] = useState(joinList(profile?.allergies));
  const [conditions, setConditions] = useState(joinList(profile?.chronic_conditions));
  const [medications, setMedications] = useState(joinList(profile?.medications));
  const [surgeries, setSurgeries] = useState(joinList(profile?.surgeries));
  const [familyHistory, setFamilyHistory] = useState(joinList(profile?.family_history));
  const [notes, setNotes] = useState(profile?.notes ?? "");
  const saveProfile = useSaveMedicalProfile();

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await saveProfile.mutateAsync({
        blood_type: bloodType || null,
        dietary_preference: dietaryPreference || null,
        allergies: splitList(allergies),
        chronic_conditions: splitList(conditions),
        medications: splitList(medications),
        surgeries: splitList(surgeries),
        family_history: splitList(familyHistory),
        // Not edited here; kept so saving the form does not erase it.
        dietary_restrictions: profile?.dietary_restrictions ?? [],
        notes,
      });
      toast.success("Medical profile saved.");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Failed to save medical profile."));
    }
  };

  const listField = (id: string, label: string, value: string, set: (v: string) => void, placeholder: string) => (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-slate-300">{label}</Label>
      <Input id={id} placeholder={placeholder} value={value} onChange={(e) => set(e.target.value)} className={inputClass} />
    </div>
  );

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="text-slate-200">Medical Profile</CardTitle>
        <p className="text-sm text-slate-400">
          Allergies, conditions and diet preference shape your plans and suggestions. Separate items with commas.
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Blood Type</Label>
              <OptionSelect
                value={bloodType}
                onChange={setBloodType}
                placeholder="Select blood type"
                options={BLOOD_TYPES.map((bt) => ({ value: bt, label: bt }))}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Diet Preference</Label>
              <OptionSelect value={dietaryPreference} onChange={setDietaryPreference} placeholder="Select preference" options={DIET_PREFERENCES} />
            </div>
          </div>
          {listField("allergies", "Allergies", allergies, setAllergies, "e.g. dairy, nuts, shellfish")}
          {listField("conditions", "Chronic Conditions", conditions, setConditions, "e.g. diabetes, hypertension")}
          {listField("medications", "Current Medications", medications, setMedications, "e.g. metformin, lisinopril")}
          {listField("surgeries", "Past Surgeries", surgeries, setSurgeries, "e.g. appendectomy (2019)")}
          {listField("family-history", "Family History", familyHistory, setFamilyHistory, "e.g. heart disease, type 2 diabetes")}
          <div className="space-y-2">
            <Label htmlFor="notes" className="text-slate-300">Additional Notes</Label>
            <Textarea
              id="notes"
              placeholder="Anything else your plans should take into account..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className={`${inputClass} min-h-[80px]`}
            />
          </div>
          <SaveButton pending={saveProfile.isPending} label="Save Medical Profile" />
        </form>
      </CardContent>
    </Card>
  );
}

function PasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const changePassword = useChangePassword();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next.length < 8) {
      toast.error("New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      toast.error("New passwords do not match.");
      return;
    }
    try {
      await changePassword.mutateAsync({ current_password: current, new_password: next });
      setCurrent("");
      setNext("");
      setConfirm("");
      toast.success("Password changed. Other devices have been signed out.");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not change your password."));
    }
  };

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="text-slate-200">Password</CardTitle>
        <p className="text-sm text-slate-400">Changing it signs you out on every other device.</p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="current-password" className="text-slate-300">Current password</Label>
              <Input id="current-password" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} className={inputClass} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-password" className="text-slate-300">New password</Label>
              <Input id="new-password" type="password" autoComplete="new-password" minLength={8} value={next} onChange={(e) => setNext(e.target.value)} className={inputClass} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-new-password" className="text-slate-300">Confirm new password</Label>
              <Input id="confirm-new-password" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className={inputClass} required />
            </div>
          </div>
          <Button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white" disabled={changePassword.isPending}>
            {changePassword.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KeyRound className="mr-2 h-4 w-4" />}
            Change Password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function DangerZone() {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const deleteAccount = useDeleteAccount();

  const handleDelete = async () => {
    try {
      await deleteAccount.mutateAsync(password);
      toast.success("Your account and all of its data have been deleted.");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not delete your account."));
    }
  };

  return (
    <Card className="bg-slate-900 border-red-500/30">
      <CardHeader>
        <CardTitle className="text-red-400">Delete account</CardTitle>
        <p className="text-sm text-slate-400">
          Permanently deletes your account, reports, analyses, plans and progress. This cannot be undone.
        </p>
      </CardHeader>
      <CardContent>
        <Button
          variant="outline"
          className="border-red-500/40 bg-transparent text-red-400 hover:bg-red-500/10 hover:text-red-300"
          onClick={() => {
            setPassword("");
            setOpen(true);
          }}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete my account
        </Button>
        <ConfirmDialog
          open={open}
          onOpenChange={setOpen}
          title="Delete your account?"
          description="Everything will be erased: your reports, analyses, plans and progress. Enter your password to confirm."
          confirmLabel="Delete everything"
          destructive
          pending={deleteAccount.isPending}
          confirmDisabled={!password}
          onConfirm={handleDelete}
        >
          <div className="space-y-2">
            <Label htmlFor="delete-password" className="text-slate-300">Password</Label>
            <Input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </div>
        </ConfirmDialog>
      </CardContent>
    </Card>
  );
}

function CardPlaceholder() {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardContent className="flex items-center gap-3 p-6 text-slate-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading...
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  // Refreshes the stored copy of the profile from the API.
  useCurrentUser();
  // isPending (not isLoading) also covers the moment before the session loads,
  // when the query is still disabled.
  const { data: medicalProfile, isPending: medicalLoading } = useMedicalProfile();

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Settings</h2>
        <p className="text-slate-400 mt-1">Manage your profile, medical information and account.</p>
      </div>

      {/* Keyed so the forms re-seed when fresher data arrives, without effects. */}
      {user ? <ProfileCard key={`${user.id}:${user.updated_at ?? ""}`} user={user} /> : <CardPlaceholder />}
      {medicalLoading ? (
        <CardPlaceholder />
      ) : (
        <MedicalCard key={medicalProfile?.updated_at ?? "new"} profile={medicalProfile ?? null} />
      )}
      <PasswordCard />
      <DangerZone />
    </div>
  );
}
