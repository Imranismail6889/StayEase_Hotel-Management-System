/* REST client: attaches the saved access token and unwraps the API envelope. */
const TOKEN_KEY = 'stayease.accessToken';

async function requestApi(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.set('Authorization', 'Bearer ' + token);
  const response = await fetch('/api' + path, { ...options, headers });
  if (response.status === 401 && token) {
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new CustomEvent('stayease:auth-expired'));
  }
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    if (!response.ok) throw new Error('The request could not be completed.');
    return response;
  }
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    const problem = payload.error || {};
    const err = new Error(problem.message || 'The request could not be completed.');
    err.code = problem.code;
    err.details = problem.details;
    throw err;
  }
  return payload.data;
}

function apiBooking(item) {
  const status = item.status_code || String(item.status || '').toLowerCase().replaceAll(' ', '_');
  return {
    ...item, id: item.booking_ref || item.id, roomId: item.room_id,
    checkin: item.check_in_date || item.checkin, checkout: item.check_out_date || item.checkout,
    total: item.total_amount ?? item.total,
    status: status === 'checked_out' ? 'Completed' : status.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
  };
}

const api = {
  request: requestApi,
  token: () => localStorage.getItem(TOKEN_KEY),
  async getRooms(query = {}) {
    const params = new URLSearchParams({ per_page: '100', ...query });
    const result = await requestApi('/rooms?' + params.toString());
    return result.items;
  },
  async getRoom(id) { return requestApi('/rooms/' + encodeURIComponent(id)); },
  async getRoomReviews(id) { return requestApi('/rooms/' + encodeURIComponent(id) + '/reviews'); },
  async login(email, password) {
    const result = await requestApi('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
    localStorage.setItem(TOKEN_KEY, result.token);
    return result.user;
  },
  async register(name, email, password) {
    const result = await requestApi('/auth/register', { method: 'POST', body: JSON.stringify({ name, email, password }) });
    localStorage.setItem(TOKEN_KEY, result.token);
    return result.user;
  },
  async me() { return requestApi('/auth/me'); },
  async updateProfile(data) { return requestApi('/auth/me', { method: 'PUT', body: JSON.stringify(data) }); },
  async changePassword(current_password, new_password) {
    return requestApi('/auth/password', { method: 'PUT', body: JSON.stringify({ current_password, new_password }) });
  },
  async forgotPassword(email) { return requestApi('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }); },
  async getBookings() { return (await requestApi('/bookings')).map(apiBooking); },
  async createBooking(draft) {
    const digits = String(draft.card || '').replace(/\D/g, '');
    const method = draft.payment === 'Pay at the hotel' ? 'upi' : String(draft.payment || 'Credit card').toLowerCase().replaceAll(' ', '_');
    const result = await requestApi('/bookings', { method: 'POST', body: JSON.stringify({
      room_id: draft.roomId, check_in: draft.checkin, check_out: draft.checkout,
      guests: draft.guests, extras: draft.extras || [], promo_code: draft.promo || '',
      method, card_last4: digits.slice(-4), card_brand: digits.startsWith('4') ? 'Visa' : 'Card',
      special_requests: draft.special_requests || '',
    }) });
    return apiBooking(result);
  },
  async quote(draft) {
    return requestApi('/bookings/quote', { method: 'POST', body: JSON.stringify({
      room_id: draft.roomId, check_in: draft.checkin, check_out: draft.checkout,
      guests: draft.guests || 1, extras: draft.extras || [], promo_code: draft.promo || '',
    }) });
  },
  async cancelBooking(id) { return requestApi('/bookings/' + encodeURIComponent(id) + '/cancel', { method: 'POST' }); },
  async modifyBooking(id, checkin, checkout, guests) {
    return apiBooking(await requestApi('/bookings/' + encodeURIComponent(id) + '/modify', { method: 'PUT', body: JSON.stringify({ check_in: checkin, check_out: checkout, guests }) }));
  },
  async processPayment() { return { ok: true }; },
  async applyPromo(code, nights = 1) {
    const result = await requestApi('/promos/validate', { method: 'POST', body: JSON.stringify({ code, nights }) });
    if (!result.valid) throw new Error(result.reason);
    return { discount: result.discount_percent / 100, percent: result.discount_percent };
  },
  async submitReview(review) {
    const items = await requestApi('/bookings');
    const eligible = items.find(item => item.room_id === review.room && item.status_code === 'checked_out');
    if (!eligible) throw new Error('Share a review after a completed stay.');
    return requestApi('/reviews', { method: 'POST', body: JSON.stringify({ booking_id: eligible.numeric_id, rating: review.rating, comment: review.text }) });
  },
  async getMyReviews() { return requestApi('/reviews'); },
  async getLoyaltyHistory() { return requestApi('/loyalty'); },
  async subscribeNewsletter(email) { return requestApi('/newsletter/subscribe', { method: 'POST', body: JSON.stringify({ email }) }); },
  async getFavorites() { return requestApi('/favorites'); },
  async addFavorite(room_id) { return requestApi('/favorites', { method: 'POST', body: JSON.stringify({ room_id }) }); },
  async removeFavorite(room_id) { return requestApi('/favorites/' + room_id, { method: 'DELETE' }); },
  async getNotifications() { return requestApi('/notifications'); },
  async markNotificationRead(id) { return requestApi('/notifications/' + id + '/read', { method: 'PUT' }); },
  async getAdminStats() { return requestApi('/admin/stats'); },
  async getAdminBookings() {
    const result = await requestApi('/admin/bookings?per_page=100');
    return { ...result, items: result.items.map(apiBooking) };
  },
  async getAdminCustomers(query = '') { return requestApi('/admin/customers?per_page=100&search=' + encodeURIComponent(query)); },
  async getCustomer(id) { return requestApi('/admin/customers/' + id); },
  async updateBookingStatus(id, status) { return requestApi('/admin/bookings/' + encodeURIComponent(id) + '/status', { method: 'PATCH', body: JSON.stringify({ status }) }); },
  async createRoom(data) { return requestApi('/admin/rooms', { method: 'POST', body: JSON.stringify(data) }); },
  async updateRoom(id, data) { return requestApi('/admin/rooms/' + id, { method: 'PUT', body: JSON.stringify(data) }); },
  async deleteRoom(id) { return requestApi('/admin/rooms/' + id, { method: 'DELETE' }); },
  async setRoomStatus(id, status) { return requestApi('/admin/rooms/' + id + '/status', { method: 'PATCH', body: JSON.stringify({ status: status.toLowerCase() }) }); },
  async getSettings() { return requestApi('/admin/settings'); },
  async saveSettings(settings) { return requestApi('/admin/settings', { method: 'PUT', body: JSON.stringify({ settings }) }); },
  async getPromos() { return requestApi('/admin/promos'); },
  async savePromo(data, id) { return requestApi('/admin/promos' + (id ? '/' + id : ''), { method: id ? 'PUT' : 'POST', body: JSON.stringify(data) }); },
  async deletePromo(id) { return requestApi('/admin/promos/' + id, { method: 'DELETE' }); },
  async invoice(id) { return requestApi('/bookings/' + encodeURIComponent(id) + '/invoice'); },
  async calendar(id) { return requestApi('/bookings/' + encodeURIComponent(id) + '/calendar.ics'); },
  async markAllNotificationsRead() { return requestApi('/notifications/read-all', { method: 'PUT' }); },
  async getTodayBoard() { return requestApi('/admin/today'); },
  async getActivity() { return requestApi('/admin/activity'); },
  async getAvailability(id, from, to) {
    return requestApi('/rooms/' + id + '/availability?from=' + encodeURIComponent(from) + '&to=' + encodeURIComponent(to));
  },
  async exportBookings() {
    const response = await fetch('/api/admin/bookings/export.csv', { headers: { Authorization: 'Bearer ' + (api.token() || '') } });
    if (!response.ok) throw new Error('Could not export reservations.');
    return response.blob();
  },
  logout() { localStorage.removeItem(TOKEN_KEY); },
};

window.api = api;
