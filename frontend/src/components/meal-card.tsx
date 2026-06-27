"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Clock } from "lucide-react";
import type { Meal } from "@/types";

interface MealCardProps {
  meal: Meal;
}

export function MealCard({ meal }: MealCardProps) {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base text-slate-200">{meal.name}</CardTitle>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Clock className="h-3 w-3" />
            {meal.time}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-2 mb-4">
          {meal.foods.map((food, index) => (
            <div
              key={index}
              className="flex items-center justify-between py-1.5 border-b border-slate-800 last:border-0"
            >
              <div>
                <p className="text-sm text-slate-300">{food.name}</p>
                <p className="text-xs text-slate-500">{food.quantity}</p>
              </div>
              <div className="flex gap-3 text-xs text-slate-400">
                <span>{food.calories} cal</span>
                <span>{food.protein}g P</span>
                <span>{food.carbs}g C</span>
                <span>{food.fat}g F</span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-4 pt-2 border-t border-slate-800">
          <div className="text-center">
            <p className="text-xs text-slate-500">Calories</p>
            <p className="text-sm font-semibold text-slate-200">
              {meal.total_calories}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Protein</p>
            <p className="text-sm font-semibold text-blue-400">
              {meal.total_protein}g
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Carbs</p>
            <p className="text-sm font-semibold text-amber-400">
              {meal.total_carbs}g
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Fat</p>
            <p className="text-sm font-semibold text-emerald-400">
              {meal.total_fat}g
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
