#include <array>
#include <cstdio>
#include <expected>
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace physics {
  enum class SpaceType {
    Dimension2D,
    Dimension3D
  };

  struct Vector2 {
    float x;
    float y;
  };

  struct Particle {
    std::string name;
    Vector2 position;
    Vector2 velocity;
    double mass;
    Particle(std::string name, float x, float y, double m) {
      this->name = name;
      this->position.x = x;
      this->position.y = y;
      this->velocity.x = 0.0;
      this->velocity.y = 0.0;
      this->mass = m;
    }
    ~Particle() {
      printf("Particle destroyed\n");
    }
    void update(float dt) {
      this->position.x += this->velocity.x * dt;
      this->position.y += this->velocity.y * dt;
    }
  };

  std::expected<double, std::string_view> calculate_energy(Particle& p) {
    if (p.mass <= 0.0) {
      return std::unexpected("Error: Mass must be greater than zero");
    }
    const float speed_sq = (p.velocity.x * p.velocity.x) + (p.velocity.y * p.velocity.y);
    const double kinetic_energy = 0.5 * p.mass * speed_sq;
    return kinetic_energy;
  }

} // namespace physics

int main() {
  float dt = 0.01667;
  const int max_particles = 3;
  const char* default_label = "Unassigned";
  std::array<int, 2> raw_matrix = {10, 20};
  std::unique_ptr<Particle> p_ptr = std::make_unique<Particle>("Electron", 0.0, 0.0, 9.11e-31);
  p_ptr->velocity.x = 2500.0;
  p_ptr->velocity.y = -1500.0;
  const char* status_msg = ((p_ptr->velocity.x > 0.0) ? ("Moving Right") : ("Static or Left"));
  if (const auto energy_result = calculate_energy(*(p_ptr))) {
    std::cout << "Energy: " << energy_result.value() << std::endl;
  } else {
    ((energy_result.error() == "Error: Mass must be greater than zero") ? (std::cout << "Critical: " << energy_result.error() << std::endl) : (std::cout << "Unknown simulation error" << std::endl));
  }
  if (dt > 0.0) {
    p_ptr->update(dt);
  }
  const SpaceType current_space = SpaceType::Dimension2D;
  const int dimensions = [&]() {
    switch (current_space) {
      case SpaceType::Dimension2D:
        return 2;
      case SpaceType::Dimension3D:
        return 3;
      default:
        return 0;
    }
  }();
  for (auto i = 0; i < max_particles; i++) {
    printf("Simulating step %d\n", i);
  }
  std::vector<int> sample_list = {1, 2, 3};
  const std::vector<int> squared_list = [&]() {
    using _elem_type = std::decay_t<decltype(*std::begin(sample_list))>;
    _elem_type num{};
    std::vector<std::decay_t<decltype(num * num)>> _res;
    for (const auto& _val : sample_list) {
      num = _val;
      _res.push_back(num * num);
    }
    return _res;
  }();
  const std::function<void(std::string_view)> logger = [&](std::string_view msg) -> void {
    std::cout << "[LOG]: " << msg << std::endl;
  };
  logger("Simulation finished successfully");
  return 0;
}
