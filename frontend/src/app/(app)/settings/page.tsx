"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from "@/stores/auth-store";
import { useCurrentUser } from "@/hooks/use-auth";
import api from "@/lib/api";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  useCurrentUser();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [goal, setGoal] = useState("");

  const [bloodType, setBloodType] = useState("");
  const [allergies, setAllergies] = useState("");
  const [conditions, setConditions] = useState("");
  const [medications, setMedications] = useState("");
  const [dietaryPreference, setDietaryPreference] = useState("");
  const [activityLevel, setActivityLevel] = useState("");
  const [medicalNotes, setMedicalNotes] = useState("");

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name || "");
      setEmail(user.email || "");
      setAge(user.age?.toString() || "");
      setGender(user.gender || "");
      setHeight(user.height?.toString() || "");
      setWeight(user.weight?.toString() || "");
      setGoal(user.goal || "");
    }
  }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/users/me", {
        name,
        age: age ? parseInt(age) : undefined,
        gender,
        height: height ? parseFloat(height) : undefined,
        weight: weight ? parseFloat(weight) : undefined,
        goal,
      });
      setUser(data);
      toast.success("Profile updated successfully!");
    } catch {
      toast.error("Failed to update profile. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveMedical = async () => {
    setSaving(true);
    try {
      await api.put("/users/me/medical-profile", {
        blood_type: bloodType,
        allergies: allergies
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
        chronic_conditions: conditions
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
        medications: medications
          .split(",")
          .map((m) => m.trim())
          .filter(Boolean),
        dietary_preferences: dietaryPreference,
        activity_level: activityLevel,
        notes: medicalNotes,
      });
      toast.success("Medical profile updated successfully!");
    } catch {
      toast.error("Failed to update medical profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Settings</h2>
        <p className="text-slate-400 mt-1">
          Manage your profile and medical information.
        </p>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Profile Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Full Name</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Email</Label>
              <Input
                value={email}
                disabled
                className="bg-slate-800 border-slate-700 text-slate-400"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Age</Label>
              <Input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Gender</Label>
              <Select value={gender} onValueChange={(v) => v && setGender(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select gender" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="male" className="text-slate-200 focus:bg-slate-700">Male</SelectItem>
                  <SelectItem value="female" className="text-slate-200 focus:bg-slate-700">Female</SelectItem>
                  <SelectItem value="other" className="text-slate-200 focus:bg-slate-700">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Height (cm)</Label>
              <Input
                type="number"
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Weight (kg)</Label>
              <Input
                type="number"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Health Goal</Label>
            <Select value={goal} onValueChange={(v) => v && setGoal(v)}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                <SelectValue placeholder="Select goal" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="weight_loss" className="text-slate-200 focus:bg-slate-700">Weight Loss</SelectItem>
                <SelectItem value="muscle_gain" className="text-slate-200 focus:bg-slate-700">Muscle Gain</SelectItem>
                <SelectItem value="maintenance" className="text-slate-200 focus:bg-slate-700">Maintenance</SelectItem>
                <SelectItem value="general_health" className="text-slate-200 focus:bg-slate-700">General Health</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button
            className="bg-blue-600 hover:bg-blue-700 text-white"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Profile
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Medical Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Blood Type</Label>
              <Select value={bloodType} onValueChange={(v) => v && setBloodType(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select blood type" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(
                    (bt) => (
                      <SelectItem key={bt} value={bt} className="text-slate-200 focus:bg-slate-700">
                        {bt}
                      </SelectItem>
                    )
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Activity Level</Label>
              <Select value={activityLevel} onValueChange={(v) => v && setActivityLevel(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select activity level" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="sedentary" className="text-slate-200 focus:bg-slate-700">Sedentary</SelectItem>
                  <SelectItem value="light" className="text-slate-200 focus:bg-slate-700">Lightly Active</SelectItem>
                  <SelectItem value="moderate" className="text-slate-200 focus:bg-slate-700">Moderately Active</SelectItem>
                  <SelectItem value="active" className="text-slate-200 focus:bg-slate-700">Active</SelectItem>
                  <SelectItem value="very_active" className="text-slate-200 focus:bg-slate-700">Very Active</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Allergies</Label>
            <Input
              placeholder="Comma-separated, e.g. dairy, nuts, shellfish"
              value={allergies}
              onChange={(e) => setAllergies(e.target.value)}
              className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Chronic Conditions</Label>
            <Input
              placeholder="Comma-separated, e.g. diabetes, hypertension"
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Current Medications</Label>
            <Input
              placeholder="Comma-separated, e.g. metformin, lisinopril"
              value={medications}
              onChange={(e) => setMedications(e.target.value)}
              className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Dietary Preferences</Label>
            <Select value={dietaryPreference} onValueChange={(v) => v && setDietaryPreference(v)}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                <SelectValue placeholder="Select preference" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="none" className="text-slate-200 focus:bg-slate-700">No Preference</SelectItem>
                <SelectItem value="vegetarian" className="text-slate-200 focus:bg-slate-700">Vegetarian</SelectItem>
                <SelectItem value="vegan" className="text-slate-200 focus:bg-slate-700">Vegan</SelectItem>
                <SelectItem value="keto" className="text-slate-200 focus:bg-slate-700">Keto</SelectItem>
                <SelectItem value="paleo" className="text-slate-200 focus:bg-slate-700">Paleo</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Additional Notes</Label>
            <Textarea
              placeholder="Any additional medical information..."
              value={medicalNotes}
              onChange={(e) => setMedicalNotes(e.target.value)}
              className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500 min-h-[80px]"
            />
          </div>

          <Button
            className="bg-blue-600 hover:bg-blue-700 text-white"
            onClick={handleSaveMedical}
            disabled={saving}
          >
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Medical Profile
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
